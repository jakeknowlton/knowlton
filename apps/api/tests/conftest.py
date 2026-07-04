"""Shared test fixtures.

The keystone of this suite is the in-memory SQLite database wired into the app
via ``app.dependency_overrides[get_session]``. Every endpoint and dependency
that resolves ``Depends(get_session)`` — today's auth routes and any router
added later — transparently uses the throwaway test database with no per-test
setup. New feature areas only need to add ``tests/<feature>/`` test files.
"""

import os

# Deterministic settings must be in place *before* any app module imports
# `config.settings`, which is instantiated at import time. Environment variables
# take precedence over the developer's `.env`, so the suite never depends on
# local config or touches the real `app.db`.
_ = os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
_ = os.environ.setdefault("ALGORITHM", "HS256")
_ = os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
_ = os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "90")
_ = os.environ.setdefault("DATABASE_URL", "sqlite://")

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from auth.models import User
from database import get_session
from main import app
from tests.auth.factories import auth_headers, make_user


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    """A fresh in-memory database with all tables created.

    `StaticPool` forces a single shared connection so the in-memory schema
    survives across the multiple connections SQLAlchemy may open during a test;
    `check_same_thread=False` lets the TestClient's threadpool reuse it.
    """
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """A database session bound to the per-test in-memory engine.

    Use this to arrange or assert on database state directly, bypassing the API.
    """
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    """A TestClient whose `get_session` dependency yields the test session.

    Overriding the dependency means the API and the `session` fixture share one
    database, so test arrangements and API calls see the same data.
    """

    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    # An https base URL so the test transport sends the `Secure` refresh-token
    # cookie back on subsequent requests (httpx withholds Secure cookies over
    # plain http), exercising the real cookie round-trip.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Authentication ---------------------------------------------------------
# Authentication isn't a peer feature; it's the gate in front of every protected
# endpoint, so a "logged-in client" belongs here as shared infrastructure rather
# than in any one feature's test directory. These build on the auth factories.


@pytest.fixture
def user(session: Session) -> User:
    """A default persisted user, usable as the subject of authenticated calls."""
    return make_user(session)


@pytest.fixture
def auth_client(client: TestClient, user: User) -> TestClient:
    """A TestClient pre-authenticated as `user` (token attached to all requests)."""
    _ = user  # Requested so the default user exists for auth_headers to log in as.
    client.headers.update(auth_headers(client))
    return client
