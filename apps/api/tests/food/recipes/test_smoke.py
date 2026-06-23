from fastapi.testclient import TestClient


def test_list_recipes_empty(auth_client: TestClient) -> None:
    response = auth_client.get("/recipes")

    assert response.status_code == 200
    assert response.json() == []


def test_list_recipes_requires_auth(client: TestClient) -> None:
    assert client.get("/recipes").status_code == 401
