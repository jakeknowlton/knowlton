from fastapi.testclient import TestClient
from sqlmodel import Session

from auth.models import User
from food.recipes.enums import Course, MealType
from tests.food.recipes.factories import make_ingredient, make_recipe, make_tag

# --- Filter -----------------------------------------------------------------


def test_filter_by_ingredients_is_and(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    flour = make_ingredient(session, "flour")
    sugar = make_ingredient(session, "sugar")
    _ = make_recipe(
        session, created_by=user.id, name="Cake", ingredients=[flour, sugar]
    )
    _ = make_recipe(session, created_by=user.id, name="Bread", ingredients=[flour])

    # Both ingredients required -> only the recipe that has both.
    response = auth_client.get("/recipes", params={"ingredient": [flour.id, sugar.id]})

    assert response.status_code == 200
    names = [r["name"] for r in response.json()]
    assert names == ["Cake"]


def test_filter_by_single_ingredient(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    flour = make_ingredient(session, "flour")
    sugar = make_ingredient(session, "sugar")
    _ = make_recipe(
        session, created_by=user.id, name="Cake", ingredients=[flour, sugar]
    )
    _ = make_recipe(session, created_by=user.id, name="Bread", ingredients=[flour])

    response = auth_client.get("/recipes", params={"ingredient": [flour.id]})

    names = {r["name"] for r in response.json()}
    assert names == {"Cake", "Bread"}


def test_filter_by_tag_meal_type_course_and_q(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    weeknight = make_tag(session, "weeknight")
    _ = make_recipe(
        session,
        created_by=user.id,
        name="Quick Pasta",
        tags=[weeknight],
        meal_type=MealType.DINNER,
        course=Course.MAIN,
    )
    _ = make_recipe(
        session,
        created_by=user.id,
        name="Fancy Pasta",
        meal_type=MealType.DINNER,
        course=Course.MAIN,
    )

    assert {
        r["name"]
        for r in auth_client.get("/recipes", params={"tag": [weeknight.id]}).json()
    } == {"Quick Pasta"}
    assert {
        r["name"]
        for r in auth_client.get("/recipes", params={"meal_type": "dinner"}).json()
    } == {"Quick Pasta", "Fancy Pasta"}
    assert {
        r["name"] for r in auth_client.get("/recipes", params={"q": "quick"}).json()
    } == {"Quick Pasta"}


def test_filter_no_params_returns_all(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    _ = make_recipe(session, created_by=user.id, name="A")
    _ = make_recipe(session, created_by=user.id, name="B")

    assert len(auth_client.get("/recipes").json()) == 2


# --- Similar ----------------------------------------------------------------


def test_similar_ranks_by_overlap(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    flour = make_ingredient(session, "flour")
    sugar = make_ingredient(session, "sugar")
    egg = make_ingredient(session, "egg")
    base = make_recipe(
        session, created_by=user.id, name="Base", ingredients=[flour, sugar, egg]
    )
    _ = make_recipe(
        session, created_by=user.id, name="TwoShared", ingredients=[flour, sugar]
    )
    _ = make_recipe(session, created_by=user.id, name="OneShared", ingredients=[flour])

    response = auth_client.get(f"/recipes/{base.id}/similar")

    assert response.status_code == 200
    body = response.json()
    assert [item["recipe"]["name"] for item in body] == ["TwoShared", "OneShared"]
    assert body[0]["shared_count"] == 2
    shared_names = {i["name"] for i in body[0]["shared_ingredients"]}
    assert shared_names == {"flour", "sugar"}
    # The base recipe never appears in its own similar list.
    assert "Base" not in {item["recipe"]["name"] for item in body}


def test_similar_missing_recipe_404(auth_client: TestClient) -> None:
    assert auth_client.get("/recipes/999/similar").status_code == 404


# --- Makeable ---------------------------------------------------------------


def test_makeable_respects_staples_optional_and_max_missing(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    flour = make_ingredient(session, "flour")
    salt = make_ingredient(session, "salt", is_staple=True)
    nuts = make_ingredient(session, "nuts")
    _ = make_recipe(
        session,
        created_by=user.id,
        name="Nut Loaf",
        ingredients=[flour, salt],
        optional_ingredients=[nuts],
    )

    # Nothing on hand, no slack: flour is required + non-staple -> not makeable.
    assert auth_client.get("/recipes/makeable").json() == []

    # With flour on hand: salt (staple) and nuts (optional) don't count -> makeable.
    have_flour = auth_client.get(
        "/recipes/makeable", params={"have": [flour.id]}
    ).json()
    assert len(have_flour) == 1
    assert have_flour[0]["missing_ingredients"] == []

    # Allow one missing: flour is the only missing ingredient.
    slack = auth_client.get("/recipes/makeable", params={"max_missing": 1}).json()
    assert len(slack) == 1
    assert {i["name"] for i in slack[0]["missing_ingredients"]} == {"flour"}


def test_search_requires_auth(client: TestClient) -> None:
    assert client.get("/recipes").status_code == 401
    assert client.get("/recipes/makeable").status_code == 401
    assert client.get("/recipes/1/similar").status_code == 401
