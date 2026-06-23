"""Data builders for recipes tests.

These write directly to the database (bypassing the API) so tests can arrange
catalog and recipe state for search/scaling scenarios. Mirrors the laundry
`make_load` factory.
"""

import re
from datetime import datetime, timezone

from sqlmodel import Session

from food.recipes.enums import Course, IngredientCategory, MealType, Unit
from food.recipes.models import (
    Ingredient,
    IngredientAlias,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    RecipeTag,
    Tag,
)
from food.recipes.service import normalize


def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def make_ingredient(
    session: Session,
    name: str,
    *,
    category: IngredientCategory | None = None,
    is_staple: bool = False,
) -> Ingredient:
    ingredient = Ingredient(
        name=name,
        name_normalized=normalize(name),
        category=category,
        is_staple=is_staple,
        created_at=_now(),
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


def make_alias(session: Session, alias: str, ingredient: Ingredient) -> IngredientAlias:
    assert ingredient.id is not None
    row = IngredientAlias(
        alias_normalized=normalize(alias),
        ingredient_id=ingredient.id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def make_tag(session: Session, name: str) -> Tag:
    tag = Tag(name=name, name_normalized=normalize(name), created_at=_now())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


def _ref_key(ingredient: Ingredient) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", ingredient.name_normalized)


def make_recipe(
    session: Session,
    *,
    created_by: int,
    name: str = "Test Recipe",
    ingredients: list[Ingredient] | None = None,
    optional_ingredients: list[Ingredient] | None = None,
    tags: list[Tag] | None = None,
    meal_type: MealType | None = None,
    course: Course | None = None,
    yield_quantity_num: int = 4,
    yield_quantity_den: int = 1,
    yield_unit: str = "servings",
    steps: list[str] | None = None,
) -> Recipe:
    """Persist a recipe (plus children) directly, for arranging search state.

    Each catalog ingredient becomes a required `1 piece` line; pass
    `optional_ingredients` for optional lines. `steps` are raw template strings.
    """
    now = _now()
    recipe = Recipe(
        created_at=now,
        updated_at=now,
        created_by=created_by,
        name=name,
        meal_type=meal_type,
        course=course,
        yield_quantity_num=yield_quantity_num,
        yield_quantity_den=yield_quantity_den,
        yield_unit=yield_unit,
    )

    position = 0
    for ingredient in ingredients or []:
        assert ingredient.id is not None
        recipe.ingredients.append(
            RecipeIngredient(
                ingredient_id=ingredient.id,
                ref_key=_ref_key(ingredient),
                quantity_num=1,
                quantity_den=1,
                unit=Unit.PIECE,
                position=position,
                is_optional=False,
            )
        )
        position += 1
    for ingredient in optional_ingredients or []:
        assert ingredient.id is not None
        recipe.ingredients.append(
            RecipeIngredient(
                ingredient_id=ingredient.id,
                ref_key=_ref_key(ingredient),
                quantity_num=1,
                quantity_den=1,
                unit=Unit.PIECE,
                position=position,
                is_optional=True,
            )
        )
        position += 1

    for index, text in enumerate(steps or []):
        recipe.steps.append(RecipeStep(position=index, text=text))

    for tag in tags or []:
        assert tag.id is not None
        recipe.tags.append(RecipeTag(tag_id=tag.id))

    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe
