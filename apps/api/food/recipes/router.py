from fractions import Fraction
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from auth.dependencies import get_current_active_user
from auth.models import User
from database import get_session
from food.recipes import service
from food.recipes.enums import Course, MealType
from food.recipes.models import Recipe
from food.recipes.quantities import InvalidQuantityError
from food.recipes.schemas import (
    IngredientRead,
    MakeableRecipe,
    RecipeCreate,
    RecipeRead,
    RecipeUpdate,
    SimilarRecipe,
    TagRead,
)

router = APIRouter(prefix="/recipes", tags=["recipes"])


def get_recipe_or_404(
    recipe_id: int,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> Recipe:
    """Resolve a recipe ORM row by id, 404ing if absent. Recipes are shared."""
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )
    return recipe


def _base_read(recipe: Recipe) -> RecipeRead:
    return service.build_recipe_read(recipe, factor=Fraction(1), scale_label="1")


# --- Catalog autocomplete ---------------------------------------------------
# Static routes precede the dynamic `/{recipe_id}` route. The int path param
# would not match these names anyway, but the order keeps the intent obvious.


@router.get("/ingredients", response_model=list[IngredientRead])
def list_ingredients(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[IngredientRead]:
    ingredients = service.search_ingredients(session, q, limit)
    return [IngredientRead.model_validate(item) for item in ingredients]


@router.get("/tags", response_model=list[TagRead])
def list_tags(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TagRead]:
    tags = service.search_tags(session, q, limit)
    return [TagRead.model_validate(item) for item in tags]


@router.get("/makeable", response_model=list[MakeableRecipe])
def makeable_recipes(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
    have: Annotated[list[int], Query(default_factory=list)],
    max_missing: Annotated[int, Query(ge=0)] = 0,
) -> list[MakeableRecipe]:
    return [
        MakeableRecipe(
            recipe=_base_read(recipe),
            missing_ingredients=[
                IngredientRead.model_validate(item) for item in missing
            ],
        )
        for recipe, missing in service.makeable_recipes(
            session, have_ids=have, max_missing=max_missing
        )
    ]


# --- Recipe collection ------------------------------------------------------


@router.get("", response_model=list[RecipeRead])
def list_recipes(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
    ingredient: Annotated[list[int], Query(default_factory=list)],
    tag: Annotated[list[int], Query(default_factory=list)],
    meal_type: MealType | None = None,
    course: Course | None = None,
    q: str | None = None,
) -> list[RecipeRead]:
    recipes = service.search_recipes(
        session,
        ingredient_ids=ingredient,
        tag_ids=tag,
        meal_type=meal_type,
        course=course,
        q=q,
    )
    return [_base_read(recipe) for recipe in recipes]


@router.post("", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
def create_recipe(
    body: RecipeCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RecipeRead:
    assert current_user.id is not None
    try:
        recipe = service.create_recipe(session, created_by=current_user.id, data=body)
    except service.RecipeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    return _base_read(recipe)


# --- Single recipe ----------------------------------------------------------


@router.get("/{recipe_id}", response_model=RecipeRead)
def read_recipe(
    recipe_id: int,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
    to_yield: str | None = None,
    scale: str | None = None,
) -> RecipeRead:
    try:
        recipe = service.get_recipe(session, recipe_id, to_yield=to_yield, scale=scale)
    except InvalidQuantityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )
    return recipe


@router.get("/{recipe_id}/similar", response_model=list[SimilarRecipe])
def similar_recipes(
    recipe: Annotated[Recipe, Depends(get_recipe_or_404)],
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[SimilarRecipe]:
    return [
        SimilarRecipe(
            recipe=_base_read(other),
            shared_count=shared_count,
            shared_ingredients=[IngredientRead.model_validate(item) for item in shared],
        )
        for other, shared_count, shared in service.similar_recipes(
            session, recipe, limit
        )
    ]


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    body: RecipeUpdate,
    recipe: Annotated[Recipe, Depends(get_recipe_or_404)],
    session: Annotated[Session, Depends(get_session)],
) -> RecipeRead:
    try:
        updated = service.update_recipe(session, recipe, body)
    except service.RecipeVersionConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recipe was modified since you loaded it; reload and retry",
        )
    except service.RecipeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    return _base_read(updated)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe: Annotated[Recipe, Depends(get_recipe_or_404)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    service.delete_recipe(session, recipe)
