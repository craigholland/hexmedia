from __future__ import annotations
from http import HTTPStatus
from typing import List, Set, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from hexmedia.common.settings import get_settings
from hexmedia.domain.enums.asset_kind import AssetKind
from hexmedia.services.api.deps import transactional_session
from hexmedia.services.schemas.media import (
    MediaItemCreate, MediaItemRead, MediaItemPatch,
)
from hexmedia.database.repos._mapping import to_domain_media_item
from hexmedia.services.mappers.media_item import (
    to_domain_from_create, to_read_schema, apply_patch_to_domain
)
from hexmedia.database.models.media import (
    MediaItem as DBMediaItem,
    MediaAsset as DBMediaAsset,
    Rating as DBRating
)
from hexmedia.database.models.person import (
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
    TagRead
)
cfg = get_settings()
router = APIRouter(prefix=f"{cfg.api.prefix}/media-items", tags=["media-items"])


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

@router.get("/buckets/order", response_model=List[str])
def bucket_order(
    db: Session = Depends(transactional_session),
) -> List[str]:
    # Extract buckets in ascending order that actually have items
    stmt = (
        select(DBMediaItem.media_folder)
        .group_by(DBMediaItem.media_folder)
        .order_by(DBMediaItem.media_folder.asc())
    )
    return [b for (b,) in db.execute(stmt).all() if b]

@router.get("/buckets/count", response_model=Dict[str, int])
def bucket_counts(
    db: Session = Depends(transactional_session),
) -> Dict[str, int]:
    """
    Return a mapping of { bucket_code: item_count } for all buckets that have items.
    Example: { "000": 42, "001": 17, "abc": 9 }
    """
    q = MediaQueryRepo(db)
    return q.count_media_items_by_bucket()


def _asset_full_url(base: str | None, media_folder: str, identity_name: str, rel_path: str) -> str | None:
    if not base:
        return None
    base = base.rstrip("/")
    rel_dir = f"{media_folder}/{identity_name}".strip("/")
    return f"{base}/{rel_dir}/{rel_path.lstrip('/')}"


@router.get("/by-bucket/{bucket}", response_model=List[MediaItemCardRead])
def get_media_items_by_bucket(
    bucket: str = Path(..., min_length=3, max_length=3, description="media_folder bucket (e.g., '000')"),
    include: str | None = Query(None, description="Comma list: assets,persons,tags,ratings"),
    db: Session = Depends(transactional_session),
) -> List[MediaItemCardRead]:
    """
    Return MediaItem cards for a single bucket (media_folder), newest first.
    Supports optional includes to attach related data in one round-trip.
    Also populates asset.url if PUBLIC_MEDIA_URL is set.
    """
    cfg = get_settings()
    inc = _parse_include(include)
    q = MediaQueryRepo(db)

    rows = (
        db.execute(
            select(DBMediaItem)
            .where(DBMediaItem.media_folder == bucket)
            .order_by(DBMediaItem.date_created.desc().nullslast(), DBMediaItem.id.desc())
        )
        .scalars()
        .all()
    )
    if not rows:
        return []

    domain_items = [to_domain_media_item(r) for r in rows]
    base_read_items = [to_read_schema(d) for d in domain_items]
    items: List[MediaItemCardRead] = [
        MediaItemCardRead.model_validate(b.model_dump())
        for b in base_read_items
    ]

    ids = [it.id for it in items]
    if not inc or not ids:
        return items

    # Batch-load relateds based on include flags
    assets_by_id: dict = {}
    persons_by_id: dict = {}
    rating_map: dict = {}
    tags_by_id: dict = {}

    if "assets" in inc:
        aset_rows = (
            db.execute(select(DBMediaAsset).where(DBMediaAsset.media_item_id.in_(ids)))
            .scalars()
            .all()
        )
        for a in aset_rows:
            assets_by_id.setdefault(a.media_item_id, []).append(a)

    if "persons" in inc:
        ppl_rows = db.execute(
            select(DBMediaPerson.media_item_id, DBPerson)
            .join(DBPerson, DBPerson.id == DBMediaPerson.person_id)
            .where(DBMediaPerson.media_item_id.in_(ids))
        ).all()
        for mid, person in ppl_rows:
            persons_by_id.setdefault(mid, []).append(person)

    if "ratings" in inc:
        r_rows = (
            db.execute(select(DBRating).where(DBRating.media_item_id.in_(ids)))
            .scalars()
            .all()
        )
        # If you want just the score on the card, keep int; if you prefer DTO, adapt below.
        rating_map = {r.media_item_id: int(r.score) for r in r_rows}

    if "tags" in inc:
        trepo = TagRepo(db)
        tags_by_id = trepo.batch_tags_for_items(ids)  # Dict[UUID, List[DBTag]]

    # Build DTOs, attach URLs and top-level convenience fields
    cfg = get_settings()
    public_base = cfg.public_media_base_url

    for it in items:
        # assets (+ url, + top-level thumb/contact)
        if "assets" in inc:
            aset_dtos: list[MediaAssetRead] = []
            for a in assets_by_id.get(it.id, []) or []:
                dto = MediaAssetRead.model_validate(a)
                dto.url = _asset_full_url(
                    public_base,
                    it.identity.media_folder,
                    it.identity.identity_name,
                    dto.rel_path,
                )
                aset_dtos.append(dto)

                # Populate top-level convenience URLs once
                if a.kind == AssetKind.thumb and not it.thumb_url:
                    it.thumb_url = dto.url
                elif a.kind == AssetKind.contact_sheet and not it.contact_url:
                    it.contact_url = dto.url

            it.assets = aset_dtos

        # persons
        if "persons" in inc:
            it.persons = [PersonRead.model_validate(p) for p in (persons_by_id.get(it.id) or [])]

        # ratings (keep as int per MediaItemCardRead schema)
        if "ratings" in inc:
            score = rating_map.get(it.id)
            it.rating = int(score) if score is not None else None

        # tags
        if "tags" in inc:
            it.tags = [TagRead.model_validate(t) for t in (tags_by_id.get(it.id) or [])]

    return items
