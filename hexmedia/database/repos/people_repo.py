from __future__ import annotations
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from hexmedia.database.models.person import (
    Person as DBPerson,
    MediaPerson as DBMediaPerson,
)
from hexmedia.database.models.media import MediaItem as DBMediaItem  # for existence checks


class SqlAlchemyPeopleRepo:
    def __init__(self, session: Session) -> None:
        self.db = session

    # -------- People (CRUD) --------

    def get(self, person_id: UUID) -> Optional[DBPerson]:
        return self.db.get(DBPerson, person_id)

    def search(self, q: str, limit: int = 25) -> List[DBPerson]:
        q = (q or "").strip().lower()
        if not q:
            stmt = select(DBPerson).order_by(DBPerson.display_name.asc()).limit(limit)
        else:
            stmt = (
                select(DBPerson)
                .where(func.lower(DBPerson.display_name).like(f"%{q}%"))
                .order_by(DBPerson.display_name.asc())
                .limit(limit)
            )
        return self.db.execute(stmt).scalars().all()

    def create(self, *, display_name: str, normalized_name: str | None = None) -> DBPerson:
        obj = DBPerson(display_name=display_name, normalized_name=normalized_name)
        self.db.add(obj)
        return obj

    def update(self, person_id: UUID, *, display_name: str | None = None, normalized_name: str | None = None) -> DBPerson:
        obj = self.get(person_id)
        if not obj:
            raise ValueError("Person not found")
        if display_name is not None:
            obj.display_name = display_name
        if normalized_name is not None:
            obj.normalized_name = normalized_name
        return obj

    def delete(self, person_id: UUID) -> None:
        obj = self.get(person_id)
        if not obj:
            return
        self.db.delete(obj)

    # -------- Media <-> Person links --------

    def list_by_media(self, media_item_id: UUID) -> List[DBPerson]:
        stmt = (
            select(DBPerson)
            .join(DBMediaPerson, DBMediaPerson.person_id == DBPerson.id)
            .where(DBMediaPerson.media_item_id == media_item_id)
            .order_by(DBPerson.display_name.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def link(self, *, media_item_id: UUID, person_id: UUID) -> DBMediaPerson:
        # Optionally ensure both sides exist:
        if not self.db.get(DBMediaItem, media_item_id):
            raise ValueError("Media item does not exist")
        if not self.db.get(DBPerson, person_id):
            raise ValueError("Person does not exist")

        # Check existing (assumes UniqueConstraint(media_item_id, person_id) on MediaPerson)
        exists_stmt = select(DBMediaPerson).where(
            and_(
                DBMediaPerson.media_item_id == media_item_id,
                DBMediaPerson.person_id == person_id,
            )
        ).limit(1)
        exists = self.db.execute(exists_stmt).scalars().first()
        if exists:
            return exists

        link = DBMediaPerson(media_item_id=media_item_id, person_id=person_id)
        self.db.add(link)
        return link

    def unlink(self, *, media_item_id: UUID, person_id: UUID) -> None:
        stmt = select(DBMediaPerson).where(
            and_(
                DBMediaPerson.media_item_id == media_item_id,
                DBMediaPerson.person_id == person_id,
            )
        ).limit(1)
        link = self.db.execute(stmt).scalars().first()
        if not link:
            return
        self.db.delete(link)
