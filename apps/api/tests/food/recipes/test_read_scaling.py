from fastapi.testclient import TestClient


def _scalable_recipe() -> dict:
    # 4 servings; 2 cups flour, 3 eggs. "Stir in half the flour" exercises a
    # per-token multiplier.
    return {
        "name": "Cake",
        "yield_quantity": "4",
        "yield_unit": "servings",
        "ingredients": [
            {
                "ref_key": "flour",
                "ingredient": "flour",
                "quantity": "2",
                "unit": "cup",
                "position": 0,
            },
            {
                "ref_key": "eggs",
                "ingredient": "egg",
                "quantity": "3",
                "position": 1,
            },
        ],
        "steps": [
            {"text": "Whisk {{ri:eggs}}.", "position": 0},
            {"text": "Stir in {{ri:flour*1/2}}.", "position": 1},
            {"text": "Bake at 350F for 30 minutes.", "position": 2},
        ],
        "tags": [],
    }


def _create(auth_client: TestClient) -> int:
    response = auth_client.post("/recipes", json=_scalable_recipe())
    assert response.status_code == 201
    return response.json()["id"]


def test_base_read_unscaled(auth_client: TestClient) -> None:
    recipe_id = _create(auth_client)

    body = auth_client.get(f"/recipes/{recipe_id}").json()

    assert body["scale"] == "1"
    assert body["effective_yield"]["quantity_display"] == "4"
    flour = next(i for i in body["ingredients"] if i["ref_key"] == "flour")
    assert flour["quantity_display"] == "2"
    assert body["steps"][0]["text_rendered"] == "Whisk 3 egg."
    # Per-token *1/2 multiplier: half of 2 cups, rendered amount + name.
    assert body["steps"][1]["text_rendered"] == "Stir in 1 cup flour."
    # Time/temperature literals are untouched.
    assert body["steps"][2]["text_rendered"] == "Bake at 350F for 30 minutes."


def test_to_yield_scales_exactly(auth_client: TestClient) -> None:
    recipe_id = _create(auth_client)

    # 4 -> 6 servings is a factor of 3/2.
    body = auth_client.get(f"/recipes/{recipe_id}", params={"to_yield": "6"}).json()

    assert body["scale"] == "1 1/2"  # 3/2 as a mixed number
    assert body["effective_yield"]["quantity_display"] == "6"
    flour = next(i for i in body["ingredients"] if i["ref_key"] == "flour")
    assert flour["quantity_display"] == "3"  # 2 * 3/2
    eggs = next(i for i in body["ingredients"] if i["ref_key"] == "eggs")
    assert eggs["quantity_num"] == 9 and eggs["quantity_den"] == 2  # 3 * 3/2
    assert eggs["quantity_display"] == "4 1/2"
    assert body["steps"][0]["text_rendered"] == "Whisk 4 1/2 egg."
    # 3 cups * 1/2 = 1 1/2 cups
    assert body["steps"][1]["text_rendered"] == "Stir in 1 1/2 cups flour."


def test_scale_multiplier(auth_client: TestClient) -> None:
    recipe_id = _create(auth_client)

    body = auth_client.get(f"/recipes/{recipe_id}", params={"scale": "1/2"}).json()

    assert body["scale"] == "1/2"
    flour = next(i for i in body["ingredients"] if i["ref_key"] == "flour")
    assert flour["quantity_display"] == "1"  # half of 2 cups


def test_read_missing_returns_404(auth_client: TestClient) -> None:
    assert auth_client.get("/recipes/999").status_code == 404


def test_read_invalid_scale_returns_422(auth_client: TestClient) -> None:
    recipe_id = _create(auth_client)
    assert (
        auth_client.get(f"/recipes/{recipe_id}", params={"scale": "0"}).status_code
        == 422
    )


def test_read_requires_auth(client: TestClient) -> None:
    assert client.get("/recipes/1").status_code == 401
