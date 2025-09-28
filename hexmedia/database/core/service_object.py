# hexmedia/database/core/service_object.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID as _UUID

from sqlalchemy import DateTime, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hexmedia.database.core.main import Base


class ServiceObject(Base):
    """
    Abstract base with common columns for all persisted models.
    Subclass this in concrete models (define __tablename__ in subclasses).
    """
    __abstract__ = True

    # Primary key
    id: Mapped[_UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),  # requires uuid-ossp (created in env.py)
    )

    # Timestamps
    date_created: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )

    # Optional provenance / metadata
    data_origin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
