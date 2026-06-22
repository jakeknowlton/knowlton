from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from auth.dependencies import get_current_active_user
from auth.models import User
from database import get_session
from home.laundry import service
from home.laundry.models import LaundryLoad
from home.laundry.schemas import LaundryLoadCreate, LaundryLoadRead, LaundryLoadUpdate

router = APIRouter(prefix="/laundry/loads", tags=["laundry"])


def get_load_or_404(
    load_id: int,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> LaundryLoad:
    """Resolve any load by id, 404ing if it does not exist.

    No ownership check: the washer and dryer are shared, so any authenticated
    user may act on any load.
    """
    load = service.get_load(session, load_id)
    if load is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Laundry load not found"
        )
    return load


@router.post("", response_model=LaundryLoadRead, status_code=status.HTTP_201_CREATED)
def create_load(
    body: LaundryLoadCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> LaundryLoadRead:
    assert current_user.id is not None
    load = service.create_load(session, created_by=current_user.id, data=body)
    return LaundryLoadRead.model_validate(load)


@router.get("", response_model=list[LaundryLoadRead])
def list_loads(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> list[LaundryLoadRead]:
    loads = service.list_loads(session)
    return [LaundryLoadRead.model_validate(load) for load in loads]


@router.patch("/{load_id}", response_model=LaundryLoadRead)
def update_load(
    body: LaundryLoadUpdate,
    load: Annotated[LaundryLoad, Depends(get_load_or_404)],
    session: Annotated[Session, Depends(get_session)],
) -> LaundryLoadRead:
    try:
        updated = service.update_load(session, load, body)
    except service.LaundryConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only one load can be in the washer or dryer at a time",
        )
    return LaundryLoadRead.model_validate(updated)


@router.delete("/{load_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_load(
    load: Annotated[LaundryLoad, Depends(get_load_or_404)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    service.delete_load(session, load)
