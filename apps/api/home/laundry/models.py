import enum
from typing import ClassVar, cast

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, text
from sqlalchemy.sql.schema import SchemaItem
from sqlmodel import Field, SQLModel


class LaundryStatus(str, enum.Enum):
    DIRTY = "dirty"
    WASHING = "washing"
    DRYING = "drying"
    FOLDING = "folding"
    DONE = "done"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    # `Enum.value` is typed `Any` upstream; this is a `str` enum, so the cast
    # restores the real element type without a runtime change.
    return [cast(str, member.value) for member in enum_cls]


class LaundryLoad(SQLModel, table=True):
    # The washer and dryer are globally shared resources. These partial unique
    # indexes enforce single-occupancy at the database level: at most one row may
    # be in the 'washing' state and at most one in the 'drying' state at a time.
    # Both dialect-specific `where` clauses are supplied so the constraint holds
    # whether the app runs on SQLite (today) or PostgreSQL (later).
    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        Index(
            "uq_one_laundry_load_washing",
            "status",
            unique=True,
            sqlite_where=text("status = 'washing'"),
            postgresql_where=text("status = 'washing'"),
        ),
        Index(
            "uq_one_laundry_load_drying",
            "status",
            unique=True,
            sqlite_where=text("status = 'drying'"),
            postgresql_where=text("status = 'drying'"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    created_at: int  # Unix timestamp
    created_by: int = Field(foreign_key="user.id")
    label: str | None = Field(default=None)
    status: LaundryStatus = Field(
        sa_column=Column(
            SAEnum(LaundryStatus, values_callable=_enum_values),
            nullable=False,
        )
    )
    washer_finish: int | None = Field(default=None)  # Unix timestamp
    dryer_finish: int | None = Field(default=None)  # Unix timestamp
