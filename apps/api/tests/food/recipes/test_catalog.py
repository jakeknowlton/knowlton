from fastapi.testclient import TestClient
from sqlmodel import Session, select

import food.recipes.service as service
from food.recipes.enums import IngredientCategory
from food.recipes.models import Ingredient
from tests.food.recipes.factories import make_alias, make_ingredient, make_tag

# --- normalize --------------------------------------------------------------


def test_normalize_collapses_and_lowercases() -> None:
    assert service.normalize("  Green   Onion ") == "green onion"
    assert service.normalize("FLOUR") == "flour"


# --- get_or_create_ingredient ----------------------------------------------


def test_get_or_create_creates_then_dedups(session: Session) -> None:
    first = service.get_or_create_ingredient(session, "Flour")
    second = service.get_or_create_ingredient(session, "  flour ")

    assert first.id == second.id
    assert session.exec(select(Ingredient)).all().__len__() == 1


def test_get_or_create_resolves_alias(session: Session) -> None:
    onion = make_ingredient(session, "green onion")
    _ = make_alias(session, "scallion", onion)

    resolved = service.get_or_create_ingredient(session, "Scallion")

    assert resolved.id == onion.id


def test_get_or_create_preserves_display_name(session: Session) -> None:
    ingredient = service.get_or_create_ingredient(session, "  Olive Oil ")
    assert ingredient.name == "Olive Oil"
    assert ingredient.name_normalized == "olive oil"


def test_get_or_create_accepts_category_and_staple(session: Session) -> None:
    salt = service.get_or_create_ingredient(
        session, "Salt", category=IngredientCategory.SPICES, is_staple=True
    )
    assert salt.category is IngredientCategory.SPICES
    assert salt.is_staple is True


# --- get_or_create_tag ------------------------------------------------------


def test_get_or_create_tag_dedups(session: Session) -> None:
    first = service.get_or_create_tag(session, "Vegan")
    second = service.get_or_create_tag(session, "vegan")
    assert first.id == second.id


# --- search endpoints -------------------------------------------------------


def test_search_ingredients_ranks_prefix_first(
    auth_client: TestClient, session: Session
) -> None:
    _ = make_ingredient(session, "chickpea")  # substring match on "pea"
    _ = make_ingredient(session, "pea")  # prefix match
    _ = make_ingredient(session, "peanut")  # prefix match

    response = auth_client.get("/recipes/ingredients", params={"q": "pea"})

    assert response.status_code == 200
    names = [row["name"] for row in response.json()]
    # Prefix matches ("pea", "peanut") rank ahead of the substring ("chickpea").
    assert names == ["pea", "peanut", "chickpea"]


def test_search_ingredients_blank_browses_all(
    auth_client: TestClient, session: Session
) -> None:
    _ = make_ingredient(session, "banana")
    _ = make_ingredient(session, "apple")

    response = auth_client.get("/recipes/ingredients")

    assert response.status_code == 200
    names = [row["name"] for row in response.json()]
    assert names == ["apple", "banana"]


def test_search_ingredients_respects_limit(
    auth_client: TestClient, session: Session
) -> None:
    for name in ["aa", "ab", "ac", "ad"]:
        _ = make_ingredient(session, name)

    response = auth_client.get("/recipes/ingredients", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_tags(auth_client: TestClient, session: Session) -> None:
    _ = make_tag(session, "weeknight")
    _ = make_tag(session, "weekend")

    response = auth_client.get("/recipes/tags", params={"q": "week"})

    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert names == {"weeknight", "weekend"}


def test_search_requires_auth(client: TestClient) -> None:
    assert client.get("/recipes/ingredients").status_code == 401
    assert client.get("/recipes/tags").status_code == 401
