from fastapi.testclient import TestClient
from sqlmodel import Session, select

from food.recipes.models import Recipe, RecipeIngredient


def _payload(**overrides: object) -> dict:
    payload: dict = {
        "name": "Soup",
        "yield_quantity": "4",
        "yield_unit": "bowls",
        "ingredients": [
            {
                "ref_key": "water",
                "ingredient": "water",
                "quantity": "4",
                "unit": "cup",
                "position": 0,
            },
            {
                "ref_key": "salt",
                "ingredient": "salt",
                "unit": "to_taste",
                "position": 1,
            },
        ],
        "steps": [{"text": "Boil {{ri:water}}.", "position": 0}],
        "tags": ["dinner"],
    }
    payload.update(overrides)
    return payload


def _create(auth_client: TestClient) -> dict:
    response = auth_client.post("/recipes", json=_payload())
    assert response.status_code == 201
    return response.json()


def test_update_full_replace_bumps_version(
    auth_client: TestClient, session: Session
) -> None:
    created = _create(auth_client)
    recipe_id = created["id"]

    update = _payload(
        name="Better Soup",
        version=1,
        ingredients=[
            {
                "ref_key": "water",
                "ingredient": "water",
                "quantity": "6",
                "unit": "cup",
                "position": 0,
            },
            {
                "ref_key": "carrot",
                "ingredient": "carrot",
                "quantity": "2",
                "position": 1,
            },
        ],
        steps=[{"text": "Simmer {{ri:carrot}} in {{ri:water}}.", "position": 0}],
        tags=["dinner", "vegetarian"],
    )
    response = auth_client.put(f"/recipes/{recipe_id}", json=update)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Better Soup"
    assert body["version"] == 2
    assert body["updated_at"] >= created["updated_at"]
    ref_keys = {i["ref_key"] for i in body["ingredients"]}
    assert ref_keys == {"water", "carrot"}  # salt dropped, carrot added
    tag_names = {t["name"] for t in body["tags"]}
    assert tag_names == {"dinner", "vegetarian"}


def test_update_preserves_id_for_unchanged_ref_key(
    auth_client: TestClient, session: Session
) -> None:
    recipe_id = _create(auth_client)["id"]
    water_before = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.ref_key == "water")
    ).one()
    water_id = water_before.id

    update = _payload(version=1)
    update["ingredients"][0]["quantity"] = "8"  # change water amount, same ref_key
    auth_client.put(f"/recipes/{recipe_id}", json=update)

    session.expire_all()
    water_after = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.ref_key == "water")
    ).one()
    # Diff-by-ref_key updates the row in place rather than delete+reinsert.
    assert water_after.id == water_id
    assert water_after.quantity_num == 8


def test_update_stale_version_returns_409(auth_client: TestClient) -> None:
    recipe_id = _create(auth_client)["id"]
    # Bump to version 2.
    assert (
        auth_client.put(f"/recipes/{recipe_id}", json=_payload(version=1)).status_code
        == 200
    )
    # Re-submitting version 1 is now stale.
    response = auth_client.put(f"/recipes/{recipe_id}", json=_payload(version=1))
    assert response.status_code == 409


def test_update_removing_referenced_ingredient_fails(
    auth_client: TestClient,
) -> None:
    recipe_id = _create(auth_client)["id"]
    # Drop the "water" line while a step still references {{ri:water}}.
    update = _payload(
        version=1,
        ingredients=[
            {
                "ref_key": "salt",
                "ingredient": "salt",
                "unit": "to_taste",
                "position": 0,
            }
        ],
    )
    response = auth_client.put(f"/recipes/{recipe_id}", json=update)
    assert response.status_code == 422


def test_update_missing_returns_404(auth_client: TestClient) -> None:
    assert auth_client.put("/recipes/999", json=_payload(version=1)).status_code == 404


def test_delete_cascades(auth_client: TestClient, session: Session) -> None:
    recipe_id = _create(auth_client)["id"]

    assert auth_client.delete(f"/recipes/{recipe_id}").status_code == 204
    assert auth_client.get(f"/recipes/{recipe_id}").status_code == 404
    assert session.exec(select(Recipe)).all() == []
    assert session.exec(select(RecipeIngredient)).all() == []


def test_delete_missing_returns_404(auth_client: TestClient) -> None:
    assert auth_client.delete("/recipes/999").status_code == 404


def test_mutations_require_auth(client: TestClient) -> None:
    assert client.put("/recipes/1", json=_payload(version=1)).status_code == 401
    assert client.delete("/recipes/1").status_code == 401
