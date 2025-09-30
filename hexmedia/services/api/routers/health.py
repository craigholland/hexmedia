# hexmedia/services/api/routers/health.py
from __future__ import annotations
from fastapi import APIRouter
from hexmedia.common.settings import get_settings

router = APIRouter()

@router.get("/healthz")
def healthz():
    s = get_settings()
    return {
        "ok": True,
        "app": s.app_name,
        "env": s.app_env,
    }
