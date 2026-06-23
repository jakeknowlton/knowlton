from sqlmodel import Session, select

from auth.models import User
from food.recipes.models import (
    Recipe,
    RecipeIngredient,
    RecipeStep,
    RecipeTag,
)
from tests.food.recipes.factories import make_ingredient, make_recipe, make_tag


def test_recipe_aggregate_persists(session: Session, user: User) -> None:
    assert user.id is not None
    flour = make_ingredient(session, "flour")
    tag = make_tag(session, "baking")

    recipe = make_recipe(
        session,
        created_by=user.id,
        ingredients=[flour],
        tags=[tag],
        steps=["Mix everything."],
    )

    assert recipe.id is not None
    assert len(recipe.ingredients) == 1
    assert len(recipe.steps) == 1
    assert len(recipe.tags) == 1


def test_delete_recipe_cascades_to_children(session: Session, user: User) -> None:
    assert user.id is not None
    flour = make_ingredient(session, "flour")
    tag = make_tag(session, "baking")
    recipe = make_recipe(
        session,
        created_by=user.id,
        ingredients=[flour],
        tags=[tag],
        steps=["Mix.", "Bake."],
    )

    session.delete(recipe)
    session.commit()

    # Children are gone via ORM cascade...
    assert session.exec(select(RecipeIngredient)).all() == []
    assert session.exec(select(RecipeStep)).all() == []
    assert session.exec(select(RecipeTag)).all() == []
    assert session.exec(select(Recipe)).all() == []
    # ...but the shared catalog rows survive.
    assert session.get(type(flour), flour.id) is not None
    assert session.get(type(tag), tag.id) is not None
