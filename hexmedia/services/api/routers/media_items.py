from __future__ import annotations
from http import HTTPStatus
from typing import List, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from hexmedia.services.api.deps import transactional_session, get_db
from hexmedia.services.schemas.media import (
    MediaItemCreate, MediaItemRead, MediaItemPatch,
)
from hexmedia.services.mappers.media_item import (
    to_domain_from_create, to_read_schema, apply_patch_to_domain
)
from hexmedia.database.models.media import (
    MediaItem as DBMediaItem,
    MediaAsset as DBMediaAsset,
    Rating as DBRating
)
from hexmedia.database.models.taxonomy import (
    Person as DBPerson,
    MediaPerson as DBMediaPerson,
)
from hexmedia.database.repos.media_repo import SqlAlchemyMediaRepo
from hexmedia.database.repos.tag_repo import TagRepo
from hexmedia.domain.entities.media_item import MediaIdentity
from hexmedia.database.repos.media_query import MediaQueryRepo

from hexmedia.services.schemas import (
    MediaAssetRead,
    MediaItemCardRead,
    PersonRead,
    TagRead,
    RatingRead
)

router = APIRouter()



@router.get("/by-identity", response_model=MediaItemRead)
def get_media_item_by_identity(
    media_folder: str = Query(...),
    identity_name: str = Query(...),
    video_ext: str = Query(...),
    session: Session = Depends(transactional_session),
) -> MediaItemRead:
    q = MediaQueryRepo(session=session)
    identity = MediaIdentity(media_folder=media_folder, identity_name=identity_name, video_ext=video_ext)
    found = q.get_by_identity(identity)
    if not found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    return to_read_schema(found)

@router.get("/{item_id}", response_model=MediaItemRead)
def get_media_item(item_id: UUID = Path(...), session: Session = Depends(transactional_session)) -> MediaItemRead:
    q = MediaQueryRepo(session=session)
    found = q.get_by_id(item_id)
    if not found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    return to_read_schema(found)

@router.patch("/{item_id}", response_model=MediaItemRead)
def patch_media_item(item_id: UUID, payload: MediaItemPatch, session: Session = Depends(transactional_session)) -> MediaItemRead:
    repo = SqlAlchemyMediaRepo(db=session)
    current = repo.get_by_id(item_id)
    if not current:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    updated = apply_patch_to_domain(current, payload)
    try:
        saved = repo.update_media_item(updated)
        return to_read_schema(saved)
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e.orig))

@router.delete("/{item_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_media_item(item_id: UUID, session: Session = Depends(transactional_session)) -> None:
    repo = SqlAlchemyMediaRepo(db=session)
    repo.delete_media_item(item_id)

@router.get("", response_model=List[MediaItemRead])
def list_media_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(transactional_session),
) -> List[MediaItemRead]:
    q = MediaQueryRepo(session=session)
    items = q.list_media_items(limit=limit, offset=offset)
    return [to_read_schema(it) for it in items]

@router.post("", response_model=MediaItemRead, status_code=HTTPStatus.CREATED)
def create_media_item(payload: MediaItemCreate, session: Session = Depends(transactional_session)) -> MediaItemRead:
    repo = SqlAlchemyMediaRepo(db=session)
    try:
        domain_item = to_domain_from_create(payload)
        created = repo.create_media_item(domain_item)  # returns Domain
        return to_read_schema(created)
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e.orig))
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

def _parse_include(include: str | None) -> Set[str]:
    if not include:
        return set()
    parts = [p.strip().lower() for p in include.split(",") if p.strip()]
    allowed = {"assets", "persons", "tags", "ratings"}
    return {p for p in parts if p in allowed}

@router.get("/by-bucket/{bucket}", response_model=List[MediaItemCardRead])
def list_media_by_bucket(
    bucket: str = Path(..., min_length=3, max_length=3, description="media_folder bucket (e.g., '000')"),
    include: str | None = Query(None, description="Comma list: assets,persons,tags,ratings"),
    db: Session = Depends(transactional_session),
) -> List[MediaItemCardRead]:
    inc = _parse_include(include)
    q = MediaQueryRepo(db)

    rows = q.list_media_by_bucket(bucket=bucket, include=inc)
    if rows is None:
        raise HTTPException(status_code=404, detail="Bucket not found or empty")

    item_ids = [r.id for r in rows]

    assets_by_id = q.batch_assets_for_items(item_ids) if "assets" in inc else {}
    persons_by_id = q.batch_persons_for_items(item_ids) if "persons" in inc else {}
    ratings_by_id = q.batch_ratings_for_items(item_ids) if "ratings" in inc else {}
    # tags_by_id = q.batch_tags_for_items(item_ids) if "tags" in inc else {}

    out: List[MediaItemCardRead] = []
    for r in rows:
        card = MediaItemCardRead.model_validate(r)
        if "assets" in inc:
            aset = assets_by_id.get(r.id, [])
            card.assets = [MediaAssetRead.model_validate(a) for a in aset]
        if "persons" in inc:
            ppl = persons_by_id.get(r.id, [])
            card.persons = [PersonRead.model_validate(p) for p in ppl]
        if "ratings" in inc:
            card.rating = ratings_by_id.get(r.id)
        # if "tags" in inc:
        #     card.tags = [TagRead.model_validate(t) for t in tags_by_id.get(r.id, [])]
        out.append(card)

    return out

@router.get("/buckets/order", response_model=List[str])
def bucket_order(
    db: Session = Depends(transactional_session),
) -> List[str]:
    # Extract buckets in ascending order that actually have items
    stmt = select(DBMediaItem.media_folder).group_by(DBMediaItem.media_folder).order_by(DBMediaItem.media_folder.asc())
    return [b for (b,) in db.execute(stmt).all() if b]

@router.get("/by-bucket/{bucket}", response_model=List[MediaItemCardRead])
def get_media_items_by_bucket(
    bucket: str,
    include: str = Query(
        "",
        description="comma-separated includes: assets,persons,ratings,tags",
        examples=["assets,persons,ratings,tags"],
    ),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[MediaItemCardRead]:
    """
    Return MediaItem cards for a single bucket (media_folder), newest first.
    Supports optional includes to attach related data in one round-trip.
    """
    # 1) Load core rows (this bucket, newest first, up to limit)
    stmt = (
        select(DBMediaItem)
        .where(DBMediaItem.media_folder == bucket)
        .order_by(DBMediaItem.date_created.desc().nullslast(), DBMediaItem.id.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return []

    # Base card DTOs (inherits MediaItemRead; from_attributes is enabled there)
    items: List[MediaItemCardRead] = [MediaItemCardRead.model_validate(r) for r in rows]
    ids = [it.id for it in items]

    # Parse include flags
    include_set = {s.strip().lower() for s in include.split(",") if s.strip()}
    if not include_set or not ids:
        return items

    # 2) Assets
    if "assets" in include_set:
        assets = (
            db.execute(select(DBMediaAsset).where(DBMediaAsset.media_item_id.in_(ids)))
            .scalars()
            .all()
        )
        assets_map: dict = {}
        for a in assets:
            assets_map.setdefault(a.media_item_id, []).append(a)
        for it in items:
            it.assets = [MediaAssetRead.model_validate(a) for a in assets_map.get(it.id, [])]

    # 3) Persons
    if "persons" in include_set:
        rows_p = db.execute(
            select(DBMediaPerson.media_item_id, DBPerson)
            .join(DBPerson, DBPerson.id == DBMediaPerson.person_id)
            .where(DBMediaPerson.media_item_id.in_(ids))
        ).all()
        persons_map: dict = {}
        for mid, person in rows_p:
            persons_map.setdefault(mid, []).append(person)
        for it in items:
            it.persons = [PersonRead.model_validate(p) for p in persons_map.get(it.id, [])]

    # 4) Ratings
    if "ratings" in include_set:
        ratings = (
            db.execute(select(DBRating).where(DBRating.media_item_id.in_(ids)))
            .scalars()
            .all()
        )
        rating_map = {r.media_item_id: r for r in ratings}
        for it in items:
            r = rating_map.get(it.id)
            it.rating = RatingRead.model_validate(r) if r else None

    # 5) Tags
    if "tags" in include_set:
        trepo = TagRepo(db)
        tag_map = trepo.batch_tags_for_items(ids)  # Dict[UUID, List[DBTag]]
        for it in items:
            tags = tag_map.get(it.id) or []
            it.tags = [TagRead.model_validate(t) for t in tags]

    return items
