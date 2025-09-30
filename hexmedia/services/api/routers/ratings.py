from __future__ import annotations

from http import HTTPStatus
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from hexmedia.database.models.media import MediaItem, Rating
from hexmedia.services.schemas import RatingCreate, RatingRead
from hexmedia.services.api.deps import get_db

router = APIRouter()

def _to_out(r: Rating) -> RatingRead:
    return RatingRead.model_validate(r)

@router.put("/media-items/{item_id}", response_model=RatingRead, status_code=HTTPStatus.CREATED)
def put_rating(item_id: str = Path(...), payload: RatingCreate = ..., db: Session = Depends(get_db)) -> RatingRead:
    item = db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")

    # upsert-like: one rating per item (PK is media_item_id)
    rating = db.get(Rating, item_id)
    if rating:
        rating.score = payload.score
    else:
        rating = Rating(media_item_id=item_id, score=payload.score)
        db.add(rating)

    db.flush()
    db.refresh(rating)
    return _to_out(rating)

@router.get("/media-items/{item_id}", response_model=RatingRead)
def get_rating(item_id: str, db: Session = Depends(get_db)) -> RatingRead:
    rating = db.get(Rating, item_id)
    if not rating:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Rating not found")
    return _to_out(rating)

@router.delete("/media-items/{item_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_rating(item_id: str, db: Session = Depends(get_db)) -> None:
    rating = db.get(Rating, item_id)
    if not rating:
        return
    db.delete(rating)
    db.flush()
