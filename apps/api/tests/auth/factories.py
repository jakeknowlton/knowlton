"""Reusable data builders for tests.

These keep test bodies focused on behavior rather than setup boilerplate. They
write through the real service layer / session so the arranged state matches
what production code would produce.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from auth.models import User
from auth.schemas import UserCreate
from auth.service import create_user

# Enjoy - https://xkcd.com/936/
DEFAULT_PASSWORD = "correct-horse-battery-staple"


def make_user(
    session: Session,
    *,
    username: str = "alice",
    password: str = DEFAULT_PASSWORD,
    disabled: bool = False,
) -> User:
    """Create and persist a user directly via the service layer."""
    user = create_user(session, UserCreate(username=username, password=password))
    if disabled:
        user.disabled = True
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def login(
    client: TestClient,
    *,
    username: str = "alice",
    password: str = DEFAULT_PASSWORD,
):
    """Hit the token endpoint and return the raw response.

    On success the refresh token is set as a cookie on ``client``'s jar, so
    follow-up ``/auth/refresh`` and ``/auth/logout`` calls send it automatically.
    Read its value with :func:`refresh_cookie`.
    """
    return client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )


def refresh_cookie(client: TestClient) -> str | None:
    """Return the refresh token currently held in the client's cookie jar."""
    return client.cookies.get("refresh_token")


def auth_headers(
    client: TestClient,
    *,
    username: str = "alice",
    password: str = DEFAULT_PASSWORD,
) -> dict[str, str]:
    """Return an Authorization header for an existing user.

    The user must already exist (e.g. via `make_user`).
    """
    response = login(client, username=username, password=password)
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
