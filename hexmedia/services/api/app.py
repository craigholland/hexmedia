from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hexmedia.common.settings import get_settings
from hexmedia.services.api.routers import media_items, ratings, tags, people, ingest

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
    app.include_router(media_items.router, prefix=f"{cfg.api.prefix}/media-items", tags=["media-items"])
    app.include_router(ratings.router, prefix=f"{cfg.api.prefix}/ratings", tags=["ratings"])
    app.include_router(tags.router, prefix=f"{cfg.api.prefix}/tags", tags=["tags"])
    app.include_router(people.router, prefix=f"{cfg.api.prefix}/people", tags=["people"])
    app.include_router(ingest.router, prefix=f"{cfg.api.prefix}/ingest", tags=["ingest"])

    return app

app = create_app()
