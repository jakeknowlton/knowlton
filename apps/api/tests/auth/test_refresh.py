from fastapi.testclient import TestClient
from sqlmodel import Session, select

from auth.models import RefreshToken
from auth.service import create_refresh_token
from auth.utils import now_timestamp
from tests.auth.factories import login, make_user, refresh_cookie


def _refresh(client: TestClient, token: str | None = None):
    """POST /auth/refresh.

    With no ``token`` the cookie already in the jar (from ``login``) is used.
    Passing ``token`` injects exactly that value as the refresh cookie, isolating
    the jar so a single, specific token reaches the server.
    """
    if token is None:
        return client.post("/auth/refresh")
    client.cookies.clear()
    return client.post("/auth/refresh", cookies={"refresh_token": token})


def test_refresh_returns_new_access_token(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    login(client, username="alice")

    response = _refresh(client)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert "refresh_token" not in body


def test_refresh_rotates_cookie(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    login(client, username="alice")
    old = refresh_cookie(client)

    _refresh(client)

    assert refresh_cookie(client) != old


def test_refresh_old_token_invalid_after_rotation(
    client: TestClient, session: Session
) -> None:
    make_user(session, username="alice")
    login(client, username="alice")
    old = refresh_cookie(client)
    assert old is not None
    _refresh(client)  # rotates the jar cookie to a fresh token

    # Re-present the rotated-out token; single-use semantics must reject it.
    response = _refresh(client, old)

    assert response.status_code == 401


def test_refresh_without_cookie_returns_401(client: TestClient) -> None:
    response = _refresh(client)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


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
