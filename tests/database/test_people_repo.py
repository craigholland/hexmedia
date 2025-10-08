# tests/database/test_people_repo.py
from hexmedia.database.repos.people_repo import SqlAlchemyPeopleRepo
from hexmedia.database.models.media import MediaItem
from hexmedia.domain.enums.media_kind import MediaKind


def _mk_media(session, folder="000", name="abcd1234efgh", ext="mp4"):
    m = MediaItem(
        kind=MediaKind.video,
        media_folder=folder,
        identity_name=name,
        video_ext=ext,
        title="Repo Test",
    )
    session.add(m)
    session.flush()
    return m


def test_repo_crud_and_linking(db):
    repo = SqlAlchemyPeopleRepo(db)

    # create
    p = repo.create(display_name="Alice Smith")
    db.flush()
    assert p.id is not None

    # get & search
    got = repo.get(p.id)
    assert got and got.display_name == "Alice Smith"

    results = repo.search("alice", limit=10)
    assert any(r.id == p.id for r in results)

    # update
    repo.update(p.id, display_name="Alice S.")
    db.flush()
    assert repo.get(p.id).display_name == "Alice S."

    # link to media
    m = _mk_media(db)
    link = repo.link(media_item_id=m.id, person_id=p.id)
    assert link.media_item_id == m.id and link.person_id == p.id

    # idempotent link should not duplicate
    link2 = repo.link(media_item_id=m.id, person_id=p.id)
    assert link2.media_item_id == m.id and link2.person_id == p.id

    # list_by_media
    lst = repo.list_by_media(m.id)
    assert any(x.id == p.id for x in lst)

    # unlink
    repo.unlink(media_item_id=m.id, person_id=p.id)
    db.flush()
    lst2 = repo.list_by_media(m.id)
    assert all(x.id != p.id for x in lst2)

    # delete person
    repo.delete(p.id)
    db.flush()
    assert repo.get(p.id) is None