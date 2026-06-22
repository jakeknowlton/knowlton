from fastapi.testclient import TestClient
from sqlmodel import Session, select

from auth.models import RefreshToken
from auth.service import create_refresh_token
from auth.utils import now_timestamp
from tests.auth.factories import login, make_user


def _refresh(client: TestClient, token: str):
    return client.post("/auth/refresh", json={"refresh_token": token})


def test_refresh_returns_new_token_pair(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    old = login(client, username="alice").json()["refresh_token"]

    response = _refresh(client, old)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_rotates_token(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    old = login(client, username="alice").json()["refresh_token"]

    new = _refresh(client, old).json()["refresh_token"]

    assert new != old


def test_refresh_old_token_invalid_after_rotation(
    client: TestClient, session: Session
) -> None:
    make_user(session, username="alice")
    old = login(client, username="alice").json()["refresh_token"]
    _refresh(client, old)

    # Reusing a rotated-out token must fail (single-use semantics).
    response = _refresh(client, old)

    assert response.status_code == 401


def test_refresh_invalid_token_returns_401(client: TestClient) -> None:
    response = _refresh(client, "this-token-does-not-exist")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_expired_token_returns_401_and_is_deleted(
    client: TestClient, session: Session
) -> None:
    user = make_user(session, username="alice")
    token = create_refresh_token(session, user)
    # Force the token to be expired.
    db_token = session.exec(
        select(RefreshToken).where(RefreshToken.token == token)
    ).one()
    db_token.expires_at = now_timestamp() - 1
    session.add(db_token)
    session.commit()

    response = _refresh(client, token)

    assert response.status_code == 401
    remaining = session.exec(
        select(RefreshToken).where(RefreshToken.token == token)
    ).first()
    assert remaining is None
