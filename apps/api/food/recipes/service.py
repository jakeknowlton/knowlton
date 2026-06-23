"""Service layer for the recipes domain.

Holds the catalog get-or-create/search logic (Phase 2); recipe CRUD, scaling,
and search are added in later phases. Functions raise domain exceptions that the
router maps to HTTP status codes.
"""

import re
from collections.abc import Sequence
from datetime import datetime, timezone
from fractions import Fraction

from sqlalchemy import case, distinct, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from food.recipes.enums import Course, IngredientCategory, MealType
from food.recipes.models import (
    Ingredient,
    IngredientAlias,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    RecipeTag,
    Tag,
)
from food.recipes.quantities import (
    format_quantity,
    from_columns,
    parse_quantity,
    to_columns,
)
from food.recipes.rendering import IngredientRef, extract_refs, render
from food.recipes.schemas import (
    EffectiveYield,
    IngredientRead,
    RecipeCreate,
    RecipeIngredientRead,
    RecipeIngredientWrite,
    RecipeRead,
    RecipeStepRead,
    RecipeUpdate,
    TagRead,
)

_WHITESPACE = re.compile(r"\s+")


def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def normalize(name: str) -> str:
    """Lowercase, strip, and collapse internal whitespace — the catalog dedup key."""
    return _WHITESPACE.sub(" ", name.strip().lower())


def _like_pattern(query: str) -> str:
    """Escape LIKE wildcards in user input so they match literally."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped


# --- Catalog: ingredients ---------------------------------------------------


def _find_ingredient(session: Session, normalized: str) -> Ingredient | None:
    """Resolve a normalized name to an ingredient, by primary name then alias."""
    ingredient = session.exec(
        select(Ingredient).where(Ingredient.name_normalized == normalized)
    ).first()
    if ingredient is not None:
        return ingredient
    alias = session.exec(
        select(IngredientAlias).where(IngredientAlias.alias_normalized == normalized)
    ).first()
    if alias is not None:
        return session.get(Ingredient, alias.ingredient_id)
    return None


def get_or_create_ingredient(
    session: Session,
    name: str,
    *,
    category: IngredientCategory | None = None,
    is_staple: bool = False,
) -> Ingredient:
    """Find an ingredient by normalized name or alias, creating it if absent.

    The insert runs inside a SAVEPOINT so that losing the unique-name race (two
    concurrent writers, possible on Postgres) rolls back only the failed insert
    — not an enclosing recipe transaction — after which the now-existing row is
    re-selected.
    """
    normalized = normalize(name)
    existing = _find_ingredient(session, normalized)
    if existing is not None:
        return existing

    ingredient = Ingredient(
        name=name.strip(),
        name_normalized=normalized,
        category=category,
        is_staple=is_staple,
        created_at=_now(),
    )
    session.add(ingredient)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raced = _find_ingredient(session, normalized)
        assert raced is not None  # the unique violation means a row now exists
        return raced
    return ingredient


def search_ingredients(
    session: Session, query: str | None, limit: int
) -> Sequence[Ingredient]:
    """Autocomplete over ingredients: prefix matches rank above other substrings.

    A blank query browses the catalog alphabetically (handy for a picker).
    """
    if query is None or not query.strip():
        return session.exec(
            select(Ingredient).order_by(col(Ingredient.name_normalized)).limit(limit)
        ).all()

    normalized = normalize(query)
    pattern = _like_pattern(normalized)
    return session.exec(
        select(Ingredient)
        .where(col(Ingredient.name_normalized).like(f"%{pattern}%", escape="\\"))
        .order_by(
            case(
                (
                    col(Ingredient.name_normalized).like(f"{pattern}%", escape="\\"),
                    0,
                ),
                else_=1,
            ),
            col(Ingredient.name_normalized),
        )
        .limit(limit)
    ).all()


# --- Catalog: tags ----------------------------------------------------------


def get_or_create_tag(session: Session, name: str) -> Tag:
    """Find a tag by normalized name, creating it if absent (race-safe)."""
    normalized = normalize(name)
    existing = session.exec(
        select(Tag).where(Tag.name_normalized == normalized)
    ).first()
    if existing is not None:
        return existing

    tag = Tag(name=name.strip(), name_normalized=normalized, created_at=_now())
    session.add(tag)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raced = session.exec(select(Tag).where(Tag.name_normalized == normalized)).one()
        return raced
    return tag


def search_tags(session: Session, query: str | None, limit: int) -> Sequence[Tag]:
    if query is None or not query.strip():
        return session.exec(
            select(Tag).order_by(col(Tag.name_normalized)).limit(limit)
        ).all()

    normalized = normalize(query)
    pattern = _like_pattern(normalized)
    return session.exec(
        select(Tag)
        .where(col(Tag.name_normalized).like(f"%{pattern}%", escape="\\"))
        .order_by(
            case(
                (col(Tag.name_normalized).like(f"{pattern}%", escape="\\"), 0),
                else_=1,
            ),
            col(Tag.name_normalized),
        )
        .limit(limit)
    ).all()


# --- Recipe writes ----------------------------------------------------------


class RecipeValidationError(Exception):
    """Raised when a recipe payload is internally inconsistent (-> 422).

    Covers duplicate ref_keys, step tokens that point at a missing ref_key, and
    references to an unknown ingredient id.
    """


def _validate_recipe_payload(data: RecipeCreate) -> None:
    ref_keys = [item.ref_key for item in data.ingredients]
    if len(set(ref_keys)) != len(ref_keys):
        raise RecipeValidationError("Duplicate ref_key among ingredients")

    known = set(ref_keys)
    for step in data.steps:
        for ref in extract_refs(step.text):
            if ref not in known:
                raise RecipeValidationError(
                    f"Step token references unknown ref_key {ref!r}"
                )


def _resolve_ingredient(session: Session, item: RecipeIngredientWrite) -> Ingredient:
    if item.ingredient_id is not None:
        ingredient = session.get(Ingredient, item.ingredient_id)
        if ingredient is None:
            raise RecipeValidationError(f"Unknown ingredient_id {item.ingredient_id}")
        return ingredient
    # The schema guarantees exactly one of ingredient / ingredient_id is set.
    assert item.ingredient is not None
    return get_or_create_ingredient(session, item.ingredient)


def _build_children(
    session: Session, data: RecipeCreate
) -> tuple[list[RecipeIngredient], list[RecipeStep], list[RecipeTag]]:
    ingredients: list[RecipeIngredient] = []
    for item in data.ingredients:
        ingredient = _resolve_ingredient(session, item)
        assert ingredient.id is not None  # persisted by get_or_create
        if item.quantity is not None:
            num, den = to_columns(parse_quantity(item.quantity))
        else:
            num = den = None
        ingredients.append(
            RecipeIngredient(
                ingredient_id=ingredient.id,
                ref_key=item.ref_key,
                quantity_num=num,
                quantity_den=den,
                unit=item.unit,
                preparation=item.preparation,
                is_optional=item.is_optional,
                section=item.section,
                position=item.position,
            )
        )

    steps = [
        RecipeStep(position=step.position, section=step.section, text=step.text)
        for step in data.steps
    ]

    seen_tag_ids: set[int] = set()
    tags: list[RecipeTag] = []
    for name in data.tags:
        tag = get_or_create_tag(session, name)
        assert tag.id is not None
        if tag.id not in seen_tag_ids:
            seen_tag_ids.add(tag.id)
            tags.append(RecipeTag(tag_id=tag.id))

    return ingredients, steps, tags


def create_recipe(session: Session, *, created_by: int, data: RecipeCreate) -> Recipe:
    """Create a recipe and its children in one transaction."""
    _validate_recipe_payload(data)
    ingredients, steps, tags = _build_children(session, data)
    num, den = to_columns(parse_quantity(data.yield_quantity))
    now = _now()
    recipe = Recipe(
        created_at=now,
        updated_at=now,
        created_by=created_by,
        version=1,
        name=data.name,
        description=data.description,
        prep_time_minutes=data.prep_time_minutes,
        cook_time_minutes=data.cook_time_minutes,
        source=data.source,
        meal_type=data.meal_type,
        course=data.course,
        yield_quantity_num=num,
        yield_quantity_den=den,
        yield_unit=data.yield_unit,
        ingredients=ingredients,
        steps=steps,
        tags=tags,
    )
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


# --- Recipe reads -----------------------------------------------------------


def get_recipe(
    session: Session,
    recipe_id: int,
    *,
    to_yield: str | None = None,
    scale: str | None = None,
) -> RecipeRead | None:
    """Read a recipe, optionally scaled.

    `to_yield` (a target yield, takes precedence) derives the factor from the
    base yield; `scale` is a direct multiplier; neither means factor 1. Both are
    parsed with `parse_quantity`, so a bad value raises `InvalidQuantityError`.
    Returns ``None`` if the recipe does not exist.
    """
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        return None

    if to_yield is not None:
        base_yield = from_columns(recipe.yield_quantity_num, recipe.yield_quantity_den)
        factor = parse_quantity(to_yield) / base_yield
    elif scale is not None:
        factor = parse_quantity(scale)
    else:
        factor = Fraction(1)

    return build_recipe_read(recipe, factor=factor, scale_label=format_quantity(factor))


def build_recipe_read(
    recipe: Recipe, *, factor: Fraction, scale_label: str
) -> RecipeRead:
    """Assemble a `RecipeRead`, scaling quantities and rendering step tokens.

    `factor` multiplies every quantity (1 for the base view); `scale_label` is
    the human string echoed back in the `scale` field.
    """
    assert recipe.id is not None  # only ever called on a persisted recipe
    ingredient_reads: list[RecipeIngredientRead] = []
    refs: dict[str, IngredientRef] = {}
    for line in recipe.ingredients:
        base = (
            from_columns(line.quantity_num, line.quantity_den)
            if line.quantity_num is not None and line.quantity_den is not None
            else None
        )
        scaled = base * factor if base is not None else None
        if scaled is not None:
            num, den = to_columns(scaled)
            display: str | None = format_quantity(scaled)
        else:
            num = den = None
            display = None
        ingredient_reads.append(
            RecipeIngredientRead(
                ref_key=line.ref_key,
                ingredient=IngredientRead.model_validate(line.ingredient),
                quantity_num=num,
                quantity_den=den,
                quantity_display=display,
                unit=line.unit,
                preparation=line.preparation,
                is_optional=line.is_optional,
                section=line.section,
                position=line.position,
            )
        )
        refs[line.ref_key] = IngredientRef(
            quantity=base, unit=line.unit, name=line.ingredient.name
        )

    step_reads = [
        RecipeStepRead(
            position=step.position,
            section=step.section,
            text_template=step.text,
            text_rendered=render(step.text, refs, factor),
        )
        for step in recipe.steps
    ]

    scaled_yield = (
        from_columns(recipe.yield_quantity_num, recipe.yield_quantity_den) * factor
    )
    effective_yield = EffectiveYield(
        quantity_display=format_quantity(scaled_yield), unit=recipe.yield_unit
    )

    return RecipeRead(
        id=recipe.id,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
        created_by=recipe.created_by,
        version=recipe.version,
        name=recipe.name,
        description=recipe.description,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        source=recipe.source,
        meal_type=recipe.meal_type,
        course=recipe.course,
        scale=scale_label,
        effective_yield=effective_yield,
        ingredients=ingredient_reads,
        steps=step_reads,
        tags=[TagRead.model_validate(link.tag) for link in recipe.tags],
    )


# --- Recipe update / delete -------------------------------------------------


class RecipeVersionConflict(Exception):
    """Raised when an update's `version` does not match the recipe's current one."""


def _sync_ingredients(session: Session, recipe: Recipe, data: RecipeCreate) -> None:
    """Reconcile ingredient lines, matching on `ref_key`.

    Existing lines are updated in place (preserving their id and the
    UNIQUE(recipe_id, ref_key) row), new ref_keys are inserted, and dropped ones
    are deleted via the delete-orphan cascade. In-place update sidesteps the
    delete-then-insert ordering hazard a blanket rebuild would face.
    """
    existing = {line.ref_key: line for line in recipe.ingredients}
    desired: set[str] = set()
    for item in data.ingredients:
        ingredient = _resolve_ingredient(session, item)
        assert ingredient.id is not None  # persisted by get_or_create
        if item.quantity is not None:
            num, den = to_columns(parse_quantity(item.quantity))
        else:
            num = den = None
        line = existing.get(item.ref_key)
        if line is None:
            recipe.ingredients.append(
                RecipeIngredient(
                    ingredient_id=ingredient.id,
                    ref_key=item.ref_key,
                    quantity_num=num,
                    quantity_den=den,
                    unit=item.unit,
                    preparation=item.preparation,
                    is_optional=item.is_optional,
                    section=item.section,
                    position=item.position,
                )
            )
        else:
            line.ingredient_id = ingredient.id
            line.quantity_num = num
            line.quantity_den = den
            line.unit = item.unit
            line.preparation = item.preparation
            line.is_optional = item.is_optional
            line.section = item.section
            line.position = item.position
        desired.add(item.ref_key)

    for ref_key, line in existing.items():
        if ref_key not in desired:
            recipe.ingredients.remove(line)


def _sync_tags(session: Session, recipe: Recipe, data: RecipeCreate) -> None:
    """Reconcile tag links, matching on `tag_id` (its natural composite key)."""
    desired: list[int] = []
    seen: set[int] = set()
    for name in data.tags:
        tag = get_or_create_tag(session, name)
        assert tag.id is not None
        if tag.id not in seen:
            seen.add(tag.id)
            desired.append(tag.id)

    existing = {link.tag_id: link for link in recipe.tags}
    for tag_id, link in existing.items():
        if tag_id not in seen:
            recipe.tags.remove(link)
    for tag_id in desired:
        if tag_id not in existing:
            recipe.tags.append(RecipeTag(tag_id=tag_id))


def update_recipe(session: Session, recipe: Recipe, data: RecipeUpdate) -> Recipe:
    """Full-aggregate replace in one transaction, guarded by optimistic version."""
    if recipe.version != data.version:
        raise RecipeVersionConflict(
            f"Expected version {recipe.version}, got {data.version}"
        )
    _validate_recipe_payload(data)

    _sync_ingredients(session, recipe, data)
    # Steps carry a surrogate id and no unique constraint, so a blanket rebuild
    # is safe (new rows get fresh ids; old ones cascade-delete).
    recipe.steps.clear()
    for step in data.steps:
        recipe.steps.append(
            RecipeStep(position=step.position, section=step.section, text=step.text)
        )
    _sync_tags(session, recipe, data)

    num, den = to_columns(parse_quantity(data.yield_quantity))
    recipe.name = data.name
    recipe.description = data.description
    recipe.prep_time_minutes = data.prep_time_minutes
    recipe.cook_time_minutes = data.cook_time_minutes
    recipe.source = data.source
    recipe.meal_type = data.meal_type
    recipe.course = data.course
    recipe.yield_quantity_num = num
    recipe.yield_quantity_den = den
    recipe.yield_unit = data.yield_unit
    recipe.version = recipe.version + 1
    recipe.updated_at = _now()

    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


def delete_recipe(session: Session, recipe: Recipe) -> None:
    """Hard-delete a recipe; children go via the ORM cascade."""
    session.delete(recipe)
    session.commit()


# --- Recipe search ----------------------------------------------------------


def _unique_ingredients(ingredients: list[Ingredient]) -> list[Ingredient]:
    """Dedupe ingredients by id, preserving first-seen order."""
    seen: set[int] = set()
    result: list[Ingredient] = []
    for ingredient in ingredients:
        assert ingredient.id is not None
        if ingredient.id not in seen:
            seen.add(ingredient.id)
            result.append(ingredient)
    return result


def search_recipes(
    session: Session,
    *,
    ingredient_ids: list[int],
    tag_ids: list[int],
    meal_type: MealType | None,
    course: Course | None,
    q: str | None,
) -> Sequence[Recipe]:
    """Filter recipes. Multiple ingredients/tags are ANDed; `q` is a name substring."""
    stmt = select(Recipe)

    if q is not None and q.strip():
        pattern = _like_pattern(q.strip())
        stmt = stmt.where(col(Recipe.name).ilike(f"%{pattern}%", escape="\\"))
    if meal_type is not None:
        stmt = stmt.where(Recipe.meal_type == meal_type)
    if course is not None:
        stmt = stmt.where(Recipe.course == course)

    wanted = set(ingredient_ids)
    if wanted:
        # A recipe matches only if it contains *every* requested ingredient.
        having_all = (
            select(RecipeIngredient.recipe_id)
            .where(col(RecipeIngredient.ingredient_id).in_(wanted))
            .group_by(col(RecipeIngredient.recipe_id))
            .having(
                func.count(distinct(col(RecipeIngredient.ingredient_id))) == len(wanted)
            )
        )
        stmt = stmt.where(col(Recipe.id).in_(having_all))

    for tag_id in set(tag_ids):
        stmt = stmt.where(
            col(Recipe.id).in_(
                select(RecipeTag.recipe_id).where(RecipeTag.tag_id == tag_id)
            )
        )

    stmt = stmt.order_by(col(Recipe.name))
    return session.exec(stmt).all()


def similar_recipes(
    session: Session, recipe: Recipe, limit: int
) -> list[tuple[Recipe, int, list[Ingredient]]]:
    """Other recipes sharing ingredients, ranked by shared count descending."""
    my_ingredient_ids = {line.ingredient_id for line in recipe.ingredients}
    if not my_ingredient_ids:
        return []

    shared = func.count(distinct(col(RecipeIngredient.ingredient_id))).label("shared")
    rows = session.exec(
        select(RecipeIngredient.recipe_id, shared)
        .where(col(RecipeIngredient.ingredient_id).in_(my_ingredient_ids))
        .where(col(RecipeIngredient.recipe_id) != recipe.id)
        .group_by(col(RecipeIngredient.recipe_id))
        .order_by(shared.desc())
        .limit(limit)
    ).all()

    results: list[tuple[Recipe, int, list[Ingredient]]] = []
    for other_id, shared_count in rows:
        other = session.get(Recipe, other_id)
        assert other is not None
        shared_ingredients = _unique_ingredients(
            [
                line.ingredient
                for line in other.ingredients
                if line.ingredient_id in my_ingredient_ids
            ]
        )
        results.append((other, shared_count, shared_ingredients))
    return results


def makeable_recipes(
    session: Session, *, have_ids: list[int], max_missing: int
) -> list[tuple[Recipe, list[Ingredient]]]:
    """Recipes a cook can (nearly) make from `have_ids`.

    A line counts as *missing* only if it is required (not optional), the
    ingredient is not a pantry staple, and its id is not on hand. Keep recipes
    with at most `max_missing` missing ingredients, fewest-missing first. This is
    presence-only — quantities are ignored until an inventory model exists.
    """
    have = set(have_ids)
    results: list[tuple[Recipe, list[Ingredient]]] = []
    for recipe in session.exec(select(Recipe).order_by(col(Recipe.name))).all():
        missing = _unique_ingredients(
            [
                line.ingredient
                for line in recipe.ingredients
                if not line.is_optional
                and not line.ingredient.is_staple
                and line.ingredient_id not in have
            ]
        )
        if len(missing) <= max_missing:
            results.append((recipe, missing))

    results.sort(key=lambda pair: len(pair[1]))
    return results
