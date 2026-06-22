from fastapi.testclient import TestClient
from sqlmodel import Session

from auth.utils import decode_token
from tests.auth.factories import DEFAULT_PASSWORD, login, make_user


def test_login_returns_token_pair(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")

    response = login(client, username="alice")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_access_token_encodes_username(
    client: TestClient, session: Session
) -> None:
    make_user(session, username="alice")

    token = login(client, username="alice").json()["access_token"]

    assert decode_token(token)["sub"] == "alice"


def test_login_wrong_password_returns_401(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")

    response = login(client, username="alice", password="wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_unknown_user_returns_401(client: TestClient) -> None:
    response = login(client, username="nobody", password=DEFAULT_PASSWORD)

    assert response.status_code == 401
