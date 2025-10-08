from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from hexmedia.common.settings import get_settings
from hexmedia.services.api.routers import media_items, ratings, tags, people, ingest, assets, media_tags, media_people

cfg = get_settings()
dev = cfg.app_env.lower() == "development"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hexmedia API",
        version="0.1.0",
        docs_url=f"{cfg.api.prefix}/docs",
        openapi_url=f"{cfg.api.prefix}/openapi.json",
    )

    allow_origins = ["*"] if dev else cfg.api.cors.allow_origins
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
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
    app.include_router(media_tags.router)

    app.include_router(media_people.router)

    # For images/videos
    app.mount("/media", StaticFiles(directory=str(cfg.media_root), check_dir=False), name="public-media")
    return app

app = create_app()
