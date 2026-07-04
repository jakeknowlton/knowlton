from fastapi.testclient import TestClient
from sqlmodel import Session

from auth.service import get_user_by_username
from tests.auth.factories import DEFAULT_PASSWORD, make_user


def test_register_returns_201_and_user(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["disabled"] is False
    assert isinstance(body["id"], int)
    # The response schema must never leak the password hash.
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_persists_hashed_password(
    client: TestClient, session: Session
) -> None:
    client.post(
        "/auth/register",
        json={"username": "alice", "password": DEFAULT_PASSWORD},
    )

    user = get_user_by_username(session, "alice")
    assert user is not None
    assert user.hashed_password != DEFAULT_PASSWORD


def test_register_duplicate_username_returns_400(
    client: TestClient, session: Session
) -> None:
    _ = make_user(session, username="alice")

    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": "another-password"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"


def test_register_missing_password_returns_422(client: TestClient) -> None:
    response = client.post("/auth/register", json={"username": "alice"})

    assert response.status_code == 422
