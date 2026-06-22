from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from home.laundry.models import LaundryLoad, LaundryStatus
from home.laundry.schemas import LaundryLoadCreate, LaundryLoadUpdate


class LaundryConflictError(Exception):
    """Raised when an operation would put a second load in the washer or dryer."""


def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def create_load(
    session: Session, *, created_by: int, data: LaundryLoadCreate
) -> LaundryLoad:
    load = LaundryLoad(
        created_by=created_by,
        created_at=_now(),
        status=LaundryStatus.DIRTY,
        label=data.label,
    )
    session.add(load)
    session.commit()
    session.refresh(load)
    return load


def list_loads(session: Session) -> Sequence[LaundryLoad]:
    return session.exec(
        select(LaundryLoad).order_by(col(LaundryLoad.created_at).desc())
    ).all()


def get_load(session: Session, load_id: int) -> LaundryLoad | None:
    return session.get(LaundryLoad, load_id)


def update_load(
    session: Session, load: LaundryLoad, data: LaundryLoadUpdate
) -> LaundryLoad:
    fields = data.model_dump(exclude_unset=True)
    if data.status is not None:
        load.status = data.status  # Any transition is permitted.
    if "label" in fields:
        load.label = data.label
    if data.washer_duration_minutes is not None:
        load.washer_finish = _now() + data.washer_duration_minutes * 60
    if data.dryer_duration_minutes is not None:
        load.dryer_finish = _now() + data.dryer_duration_minutes * 60

    session.add(load)
    try:
        session.commit()
    except IntegrityError as exc:
        # The partial unique indexes rejected a second washer/dryer occupant.
        session.rollback()
        raise LaundryConflictError from exc
    session.refresh(load)
    return load


def delete_load(session: Session, load: LaundryLoad) -> None:
    session.delete(load)
    session.commit()
