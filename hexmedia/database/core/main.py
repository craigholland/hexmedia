# hexmedia/database/core/main.py
from __future__ import annotations

from typing import Generator, Iterator, List

from sqlalchemy import MetaData, create_engine, event, Column, Table
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from hexmedia.common.settings import get_settings

_settings = get_settings()

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

_serviceobject_first = ("id", "date_created", "last_updated", "data_origin", "meta_data")

class Base(DeclarativeBase):
    # Set a default schema to keep DDL/Autogenerate explicit and consistent
    metadata = MetaData(
        schema=_settings.db_schema if _settings.db_schema and _settings.db_schema.lower() != "public" else None,
        naming_convention=NAMING_CONVENTION,
    )

    @classmethod
    def __table_cls__(cls, *args, **kw):
        """Reorder columns so ServiceObject fields come first."""
        if not args:
            return super().__table_cls__(*args, **kw)

        # Positional args are (name, metadata, *columns_and_constraints)
        name, metadata, *rest = args

        # Separate columns from other table elements (constraints, indexes passed positionally)
        cols: List[Column] = [x for x in rest if isinstance(x, Column)]
        others = [x for x in rest if not isinstance(x, Column)]

        # Stable ordering: ServiceObject fields first, then everything else in their original order
        priority = {n: i for i, n in enumerate(_serviceobject_first)}
        # Remember original index to preserve relative order among same-priority items
        original_index = {c: i for i, c in enumerate(cols)}

        cols.sort(key=lambda c: (priority.get(c.name, 10_000), original_index[c]))

        # Rebuild table with reordered columns
        return Table(name, metadata, *(cols + others), **kw)

engine = create_engine(
    _settings.database_url,                 # <- consistent with env.py
    echo=_settings.db.echo,
    pool_size=_settings.db.pool_size,
    max_overflow=_settings.db.max_overflow,
    pool_pre_ping=_settings.db.pool_pre_ping,
    pool_recycle=_settings.db.pool_recycle,
    future=True,
)

# Ensure the app schema is first, then public (so extensions remain visible)
if _settings.db_schema and _settings.db_schema.lower() != "public":
    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_conn, _):
        with dbapi_conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{_settings.db_schema}", public')


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True, autoflush=False)


def get_session() -> Iterator[Session]:
    """
    FastAPI-friendly dependency that yields a transaction-scoped Session.
    Commits on success, rolls back on error.
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
