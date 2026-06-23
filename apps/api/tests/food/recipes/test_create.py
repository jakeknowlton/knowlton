from fastapi.testclient import TestClient
from sqlmodel import Session, select

from auth.models import User
from food.recipes.models import Ingredient
from tests.food.recipes.factories import make_ingredient


def _recipe_payload(**overrides: object) -> dict:
    payload: dict = {
        "name": "Pancakes",
        "yield_quantity": "4",
        "yield_unit": "servings",
        "ingredients": [
            {
                "ref_key": "flour",
                "ingredient": "Flour",
                "quantity": "2",
                "unit": "cup",
                "position": 0,
            },
            {
                "ref_key": "salt",
                "ingredient": "Salt",
                "unit": "to_taste",
                "position": 1,
            },
        ],
        "steps": [
            {"text": "Combine {{ri:flour}} and {{ri:salt|name}}.", "position": 0},
        ],
        "tags": ["breakfast"],
    }
    payload.update(overrides)
    return payload


def test_create_round_trips(auth_client: TestClient, user: User) -> None:
    response = auth_client.post("/recipes", json=_recipe_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Pancakes"
    assert body["version"] == 1
    assert body["created_by"] == user.id
    assert body["scale"] == "1"
    assert body["effective_yield"] == {"quantity_display": "4", "unit": "servings"}

    flour = next(i for i in body["ingredients"] if i["ref_key"] == "flour")
    assert flour["quantity_display"] == "2"
    assert flour["unit"] == "cup"
    assert flour["ingredient"]["name"] == "Flour"

    salt = next(i for i in body["ingredients"] if i["ref_key"] == "salt")
    assert salt["quantity_display"] is None

    # Default token renders amount + name; |name renders just the name.
    assert body["steps"][0]["text_rendered"] == "Combine 2 cups Flour and Salt."
    assert body["tags"][0]["name"] == "breakfast"


def test_create_requires_auth(client: TestClient) -> None:
    assert client.post("/recipes", json=_recipe_payload()).status_code == 401


def test_create_reuses_existing_catalog_ingredient(
    auth_client: TestClient, session: Session
) -> None:
    make_ingredient(session, "flour")

    response = auth_client.post("/recipes", json=_recipe_payload())

    assert response.status_code == 201
    # "Flour" deduped onto the existing "flour" row — not a second one.
    flours = session.exec(
        select(Ingredient).where(Ingredient.name_normalized == "flour")
    ).all()
    assert len(flours) == 1


def test_create_by_ingredient_id(auth_client: TestClient, session: Session) -> None:
    flour = make_ingredient(session, "flour")
    payload = _recipe_payload(
        ingredients=[
            {
                "ref_key": "flour",
                "ingredient_id": flour.id,
                "quantity": "2",
                "unit": "cup",
                "position": 0,
            }
        ],
        steps=[{"text": "Use {{ri:flour}}.", "position": 0}],
    )

    response = auth_client.post("/recipes", json=payload)

    assert response.status_code == 201
    assert response.json()["ingredients"][0]["ingredient"]["id"] == flour.id


def test_create_rejects_unknown_step_token(auth_client: TestClient) -> None:
    payload = _recipe_payload(steps=[{"text": "Add {{ri:butter}}.", "position": 0}])
    response = auth_client.post("/recipes", json=payload)
    assert response.status_code == 422


def test_create_rejects_duplicate_ref_key(auth_client: TestClient) -> None:
    payload = _recipe_payload(
        ingredients=[
            {"ref_key": "flour", "ingredient": "Flour", "position": 0},
            {"ref_key": "flour", "ingredient": "Bread Flour", "position": 1},
        ],
        steps=[],
    )
    response = auth_client.post("/recipes", json=payload)
    assert response.status_code == 422


def test_create_rejects_bad_ref_key_charset(auth_client: TestClient) -> None:
    payload = _recipe_payload(
        ingredients=[{"ref_key": "All Flour", "ingredient": "Flour", "position": 0}],
        steps=[],
    )
    response = auth_client.post("/recipes", json=payload)
    assert response.status_code == 422


def test_create_rejects_invalid_quantity(auth_client: TestClient) -> None:
    payload = _recipe_payload(
        ingredients=[
            {
                "ref_key": "flour",
                "ingredient": "Flour",
                "quantity": "0",
                "unit": "cup",
                "position": 0,
            }
        ],
        steps=[],
    )
    response = auth_client.post("/recipes", json=payload)
    assert response.status_code == 422


def test_create_rejects_both_ingredient_and_id(auth_client: TestClient) -> None:
    payload = _recipe_payload(
        ingredients=[
            {
                "ref_key": "flour",
                "ingredient": "Flour",
                "ingredient_id": 1,
                "position": 0,
            }
        ],
        steps=[],
    )
    response = auth_client.post("/recipes", json=payload)
    assert response.status_code == 422
