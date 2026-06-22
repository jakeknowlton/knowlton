"""Data builders for laundry tests.

`make_load` writes directly to the database (bypassing the API) so tests can
arrange state that the API won't create directly — e.g. a load that already
occupies the washer, or a load owned by another user.
"""

from datetime import datetime, timezone

from sqlmodel import Session

from home.laundry.models import LaundryLoad, LaundryStatus


def make_load(
    session: Session,
    *,
    created_by: int,
    label: str | None = None,
    status: LaundryStatus = LaundryStatus.DIRTY,
) -> LaundryLoad:
    load = LaundryLoad(
        created_by=created_by,
        created_at=int(datetime.now(timezone.utc).timestamp()),
        status=status,
        label=label,
    )
    session.add(load)
    session.commit()
    session.refresh(load)
    return load
