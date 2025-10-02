# tests/database/test_sqlalchemy_media_repo.py
from __future__ import annotations

import pytest
from uuid import UUID

from hexmedia.database.repos.media_repo import SqlAlchemyMediaRepo
from hexmedia.database.models.media import MediaItem as DBMediaItem
from hexmedia.domain.entities.media_item import MediaItem as DomainMediaItem, MediaIdentity
from hexmedia.domain.enums.media_kind import MediaKind


def _domain_item(folder="20", name="d0c0ffee1234", ext="mp4") -> DomainMediaItem:
    ident = MediaIdentity(media_folder=folder, identity_name=name, video_ext=ext)
    return DomainMediaItem(kind=MediaKind.video, identity=ident, size_bytes=999)


def test_create_media_item_persists_core_fields(db):
    repo = SqlAlchemyMediaRepo(db)
    mi = _domain_item()

    orm = repo.create_media_item(mi)
    # Created but NOT committed here by the repo; we can flush/refresh in the session to check
    db.flush()
    db.refresh(orm)

    assert isinstance(orm, DBMediaItem)
    assert orm.media_folder == mi.media_folder
    assert orm.identity_name == mi.identity_name
    assert orm.video_ext == mi.video_ext
    assert orm.size_bytes == 999


def test_create_media_item_enforces_unique_triplet(db):
    repo = SqlAlchemyMediaRepo(db)
    mi1 = _domain_item(folder="21", name="unique000001")
    mi2 = _domain_item(folder="21", name="unique000001")  # same triplet

    repo.create_media_item(mi1)
    db.flush()

    with pytest.raises(ValueError):
        repo.create_media_item(mi2)


def test_update_and_delete_media_item(db):
    repo = SqlAlchemyMediaRepo(db)
    mi = _domain_item(folder="22", name="updel000000")

    orm = repo.create_media_item(mi)
    db.flush()
    db.refresh(orm)

    # map back to domain for update path (the repo expects domain with id)
    dom = repo.get_by_id(orm.id)
    assert dom is not None

    dom.title = "A Title"
    dom.watched = True
    dom.favorite = True

    updated = repo.update_media_item(dom)
    assert updated.title == "A Title"
    assert updated.watched is True
    assert updated.favorite is True

    # delete
    repo.delete_media_item(orm.id)
    assert db.get(DBMediaItem, orm.id) is None
