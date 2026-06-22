from pydantic import BaseModel, ConfigDict, Field

from home.laundry.models import LaundryStatus


class LaundryLoadCreate(BaseModel):
    label: str | None = None


class LaundryLoadUpdate(BaseModel):
    status: LaundryStatus | None = None
    label: str | None = None
    # When supplied, the server sets the corresponding finish timestamp to
    # now + duration. Sent when a load is moved into the washer/dryer.
    washer_duration_minutes: int | None = Field(default=None, ge=1)
    dryer_duration_minutes: int | None = Field(default=None, ge=1)


class LaundryLoadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: int
    created_by: int
    label: str | None
    status: LaundryStatus
    washer_finish: int | None
    dryer_finish: int | None
