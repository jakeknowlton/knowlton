from fastapi.testclient import TestClient
from sqlmodel import Session, select

from auth.models import RefreshToken
from tests.auth.factories import login, make_user


def _logout(client: TestClient, token: str, all_devices: bool = False):
    return client.post(
        "/auth/logout",
        json={"refresh_token": token, "all_devices": all_devices},
    )


def _refresh(client: TestClient, token: str):
    return client.post("/auth/refresh", json={"refresh_token": token})


def test_logout_returns_204(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    token = login(client, username="alice").json()["refresh_token"]

    response = _logout(client, token)

    assert response.status_code == 204


def test_logout_revokes_refresh_token(client: TestClient, session: Session) -> None:
    make_user(session, username="alice")
    token = login(client, username="alice").json()["refresh_token"]

    _logout(client, token)

    assert _refresh(client, token).status_code == 401
    remaining = session.exec(
        select(RefreshToken).where(RefreshToken.token == token)
    ).first()
    assert remaining is None


def test_logout_single_device_leaves_other_sessions(
    client: TestClient, session: Session
) -> None:
    make_user(session, username="alice")
    token_a = login(client, username="alice").json()["refresh_token"]
    token_b = login(client, username="alice").json()["refresh_token"]

    _logout(client, token_a)

    # Only the presented token is revoked; the other session survives.
    assert _refresh(client, token_b).status_code == 200


def test_logout_all_devices_revokes_every_token(
    client: TestClient, session: Session
) -> None:
    user = make_user(session, username="alice")
    token_a = login(client, username="alice").json()["refresh_token"]
    token_b = login(client, username="alice").json()["refresh_token"]

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
    alice_token = login(client, username="alice").json()["refresh_token"]
    bob_token = login(client, username="bob").json()["refresh_token"]

    _logout(client, alice_token, all_devices=True)

    # Another user's sessions must be untouched.
    assert _refresh(client, bob_token).status_code == 200


def test_logout_unknown_token_is_idempotent(client: TestClient) -> None:
    # Logging out an unknown/already-revoked token must not error.
    response = _logout(client, "this-token-does-not-exist")

    assert response.status_code == 204
