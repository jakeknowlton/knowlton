from fastapi.testclient import TestClient
from sqlmodel import Session, select

from auth.models import RefreshToken
from tests.auth.factories import login, make_user, refresh_cookie


def _logout(client: TestClient, token: str | None = None, all_devices: bool = False):
    params = {"all_devices": all_devices}
    if token is None:
        return client.post("/auth/logout", params=params)
    client.cookies.clear()
    return client.post("/auth/logout", params=params, cookies={"refresh_token": token})


def _refresh(client: TestClient, token: str):
    client.cookies.clear()
    return client.post("/auth/refresh", cookies={"refresh_token": token})


def test_logout_returns_204(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    login(client, username="alice")

    response = _logout(client)

    assert response.status_code == 204


def test_logout_revokes_refresh_token(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    login(client, username="alice")
    token = refresh_cookie(client)
    assert token is not None

    _logout(client)

    assert _refresh(client, token).status_code == 401
    remaining = session.exec(
        select(RefreshToken).where(RefreshToken.token == token)
    ).first()
    assert remaining is None


def test_logout_single_device_leaves_other_sessions(
    client: TestClient, session: Session
) -> None:
    make_user(session, username="alice")
    login(client, username="alice")
    token_a = refresh_cookie(client)
    login(client, username="alice")  # second session; jar now holds token_b
    token_b = refresh_cookie(client)
    assert token_a is not None and token_b is not None

    _logout(client, token_a)

    # Only the presented token is revoked; the other session survives.
    assert _refresh(client, token_b).status_code == 200


def test_logout_all_devices_revokes_every_token(
    client: TestClient, session: Session
) -> None:
    user = make_user(session, username="alice")
    login(client, username="alice")
    token_a = refresh_cookie(client)
    login(client, username="alice")
    token_b = refresh_cookie(client)
    assert token_a is not None and token_b is not None

    response = _logout(client, token_a, all_devices=True)

    assert response.status_code == 204
    assert _refresh(client, token_a).status_code == 401
    assert _refresh(client, token_b).status_code == 401
    remaining = session.exec(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    ).all()
    assert remaining == []


def test_logout_all_devices_only_affects_owning_user(
    client: TestClient, session: Session
) -> None:
    make_user(session, username="alice")
    make_user(session, username="bob")
    login(client, username="alice")
    alice_token = refresh_cookie(client)
    login(client, username="bob")
    bob_token = refresh_cookie(client)
    assert alice_token is not None and bob_token is not None

    _logout(client, alice_token, all_devices=True)

    # Another user's sessions must be untouched.
    assert _refresh(client, bob_token).status_code == 200


def test_logout_unknown_token_is_idempotent(client: TestClient) -> None:
    # Logging out an unknown/absent token must not error.
    response = _logout(client, "this-token-does-not-exist")

    assert response.status_code == 204
