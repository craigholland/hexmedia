# hexmedia/database/core/service_object.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import DateTime, Text, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, declared_attr


class ServiceObject:
    """
    Mixin providing common columns for persisted models.
    Use with multiple inheritance: `class MyModel(ServiceObject, Base): ...`
    """
    __abstract__ = True

    @declared_attr
    def id(cls) -> Mapped[PyUUID]:
        # requires `uuid-ossp` extension; we enable it in migrations
        return mapped_column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )

    @declared_attr
    def date_created(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.clock_timestamp(),
        )

    @declared_attr
    def last_updated(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.clock_timestamp(),
            onupdate=func.clock_timestamp(),
        )

    @declared_attr
    def data_origin(cls) -> Mapped[Optional[str]]:
        return mapped_column(Text, nullable=True)

    @declared_attr
    def meta_data(cls) -> Mapped[Optional[dict]]:
        # Use JSONB for Postgres; switch to JSON if targeting multiple DBs
        return mapped_column(JSONB, nullable=True)
