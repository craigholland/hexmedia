# tests/database/test_person_models.py
from sqlalchemy.exc import IntegrityError

from hexmedia.database.models.media import MediaItem
from hexmedia.database.models.person import (
    Person, PersonAlias, PersonAliasLink, MediaPerson
)
from hexmedia.domain.enums.media_kind import MediaKind


def _mk_media(session, folder="000", name="abcd1234efgh", ext="mp4"):
    m = MediaItem(
        kind=MediaKind.video,
        media_folder=folder,
        identity_name=name,
        video_ext=ext,
        title="Test clip",
    )
    session.add(m)
    session.flush()
    return m


def test_person_alias_many_to_many(db):
    p = Person(display_name="Jane Doe", normalized_name="jane doe")
    a1 = PersonAlias(alias="JD", alias_normalized="jd")
    a2 = PersonAlias(alias="Janie", alias_normalized="janie")

    db.add_all([p, a1, a2])
    db.flush()

    db.add_all([
        PersonAliasLink(person_id=p.id, alias_id=a1.id),
        PersonAliasLink(person_id=p.id, alias_id=a2.id),
    ])
    db.flush()
    db.refresh(p)

    assert {al.alias for al in p.aliases} == {"JD", "Janie"}

    # Global uniqueness of alias_normalized
    dup = PersonAlias(alias="JD2", alias_normalized="jd")
    db.add(dup)
    try:
        db.flush()
        assert False, "Expected unique violation on alias_normalized"
    except IntegrityError:
        db.rollback()


def test_media_person_unique_pair(db):
    m = _mk_media(db)
    p = Person(display_name="Actor One")
    db.add(p)
    db.flush()

    link1 = MediaPerson(media_item_id=m.id, person_id=p.id)
    db.add(link1)
    db.flush()

    # Try duplicate pair → relies on DB unique constraint
    dup = MediaPerson(media_item_id=m.id, person_id=p.id)
    db.add(dup)
    try:
        db.flush()
        assert False, "Expected unique violation for duplicate media/person pair"
    except IntegrityError:
        db.rollback()