from fastapi.testclient import TestClient
from sqlmodel import Session

from auth.models import User
from home.laundry.models import LaundryStatus
from tests.auth.factories import make_user
from tests.home.laundry.factories import make_load

# --- Create -----------------------------------------------------------------


def test_create_load_starts_dirty(auth_client: TestClient, user: User) -> None:
    response = auth_client.post("/laundry/loads", json={"label": "darks"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "dirty"
    assert body["label"] == "darks"
    assert body["created_by"] == user.id
    assert isinstance(body["created_at"], int)
    assert body["washer_finish"] is None
    assert body["dryer_finish"] is None


def test_create_load_requires_auth(client: TestClient) -> None:
    assert client.post("/laundry/loads", json={}).status_code == 401


# --- List -------------------------------------------------------------------


def test_list_returns_all_loads(
    auth_client: TestClient, user: User, session: Session
) -> None:
    # Loads are shared, not owned: every user sees every load.
    assert user.id is not None
    make_load(session, created_by=user.id, label="mine")
    other = make_user(session, username="bob")
    assert other.id is not None
    make_load(session, created_by=other.id, label="theirs")

    response = auth_client.get("/laundry/loads")

    assert response.status_code == 200
    labels = {load["label"] for load in response.json()}
    assert labels == {"mine", "theirs"}


# --- Update / advance -------------------------------------------------------


def test_update_advances_status(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    load = make_load(session, created_by=user.id)

    response = auth_client.patch(
        f"/laundry/loads/{load.id}", json={"status": "washing"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "washing"


def test_any_transition_is_allowed(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    load = make_load(session, created_by=user.id, status=LaundryStatus.DONE)

    response = auth_client.patch(f"/laundry/loads/{load.id}", json={"status": "dirty"})

    assert response.status_code == 200
    assert response.json()["status"] == "dirty"


def test_washer_duration_sets_finish_timestamp(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    load = make_load(session, created_by=user.id)

    response = auth_client.patch(
        f"/laundry/loads/{load.id}",
        json={"status": "washing", "washer_duration_minutes": 60},
    )

    assert response.status_code == 200
    finish = response.json()["washer_finish"]
    assert finish is not None
    assert finish > load.created_at


def test_update_cannot_change_created_at_or_created_by(
    auth_client: TestClient, user: User, session: Session
) -> None:
    # `created_at` / `created_by` are write-once; the update schema ignores them.
    assert user.id is not None
    load = make_load(session, created_by=user.id)
    original_created_at = load.created_at
    original_created_by = load.created_by

    response = auth_client.patch(
        f"/laundry/loads/{load.id}",
        json={
            "status": "washing",
            "created_at": original_created_at + 9999,
            "created_by": original_created_by + 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created_at"] == original_created_at
    assert body["created_by"] == original_created_by


# --- Single-occupancy of washer/dryer (enforced in the DB) ------------------


def test_only_one_load_in_washer(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    first = make_load(session, created_by=user.id, label="a")
    second = make_load(session, created_by=user.id, label="b")

    assert (
        auth_client.patch(
            f"/laundry/loads/{first.id}", json={"status": "washing"}
        ).status_code
        == 200
    )
    conflict = auth_client.patch(
        f"/laundry/loads/{second.id}", json={"status": "washing"}
    )

    assert conflict.status_code == 409


def test_only_one_load_in_dryer(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    first = make_load(session, created_by=user.id, label="a")
    second = make_load(session, created_by=user.id, label="b")

    assert (
        auth_client.patch(
            f"/laundry/loads/{first.id}", json={"status": "drying"}
        ).status_code
        == 200
    )
    conflict = auth_client.patch(
        f"/laundry/loads/{second.id}", json={"status": "drying"}
    )

    assert conflict.status_code == 409


def test_washer_is_shared_across_users(
    auth_client: TestClient, user: User, session: Session
) -> None:
    assert user.id is not None
    other = make_user(session, username="bob")
    assert other.id is not None
    # Another user already occupies the (globally shared) washer.
    make_load(session, created_by=other.id, status=LaundryStatus.WASHING)
    mine = make_load(session, created_by=user.id)

    conflict = auth_client.patch(
        f"/laundry/loads/{mine.id}", json={"status": "washing"}
    )

    assert conflict.status_code == 409


# --- Delete -----------------------------------------------------------------


def test_delete_load(auth_client: TestClient, user: User, session: Session) -> None:
    assert user.id is not None
    load = make_load(session, created_by=user.id)

    assert auth_client.delete(f"/laundry/loads/{load.id}").status_code == 204
    assert auth_client.get("/laundry/loads").json() == []


def test_can_update_another_users_load(
    auth_client: TestClient, session: Session
) -> None:
    # The washer/dryer are shared, so any user may advance any load.
    other = make_user(session, username="bob")
    assert other.id is not None
    theirs = make_load(session, created_by=other.id)

    response = auth_client.patch(
        f"/laundry/loads/{theirs.id}", json={"status": "washing"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "washing"


def test_update_missing_load_returns_404(auth_client: TestClient) -> None:
    response = auth_client.patch("/laundry/loads/999", json={"status": "washing"})

    assert response.status_code == 404


def test_can_delete_another_users_load(
    auth_client: TestClient, session: Session
) -> None:
    # Loads are shared, so any user may delete any load.
    other = make_user(session, username="bob")
    assert other.id is not None
    theirs = make_load(session, created_by=other.id)

    assert auth_client.delete(f"/laundry/loads/{theirs.id}").status_code == 204
    assert auth_client.get("/laundry/loads").json() == []


def test_delete_missing_load_returns_404(auth_client: TestClient) -> None:
    assert auth_client.delete("/laundry/loads/999").status_code == 404
