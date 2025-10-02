from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from hexmedia.common.settings import get_settings
from hexmedia.services.api.routers import media_items, ratings, tags, people, ingest, assets

cfg = get_settings()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Hexmedia API",
        version="0.1.0",
        docs_url=f"{cfg.api.prefix}/docs",
        openapi_url=f"{cfg.api.prefix}/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.api.cors_allow_origins,
        allow_methods=cfg.api.cors_allow_methods,
        allow_headers=cfg.api.cors_allow_headers,
        allow_credentials=cfg.api.cors_allow_credentials,
    )

    # Routers
    app.include_router(media_items.router)
    app.include_router(ratings.router)
    app.include_router(tags.router)
    app.include_router(people.router)
    app.include_router(ingest.router)

    app.include_router(assets.router)

    # For images/videos
    app.mount("/media", StaticFiles(directory=str(cfg.media_root)), name="public-media")
    return app

app = create_app()
