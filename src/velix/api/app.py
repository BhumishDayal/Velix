"""FastAPI application factory.

Singletons (embedder, extractor, index, document store, cache) live on
``app.state`` and are constructed during the lifespan startup hook so the
heavy work happens once per process. Tests construct an app with a small
``AppConfig``; production passes a real one.

CORS is permissive in dev and locked down to allowed origins in prod via
``AppConfig.cors_origins``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import (
    AppConfig,
    build_document_store,
    build_embedder,
    build_extractor,
    build_index,
)
from .cache import ExtractionCache
from .routes import documents as documents_route
from .routes import extract as extract_route
from .routes import health as health_route
from .routes import search as search_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: AppConfig = app.state.config

    embedder = build_embedder(config)
    extractor = build_extractor(config)
    index = build_index(config, embedder)
    documents = build_document_store(config)
    cache = ExtractionCache(config.cache_db_path)
    await cache.init()

    app.state.embedder = embedder
    app.state.extractor = extractor
    app.state.index = index
    app.state.documents = documents
    app.state.cache = cache

    yield

    # No teardown needed: Qdrant local client closes on GC, aiosqlite
    # opens/closes per request.


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(
        title="Velix API",
        description=(
            "Visual-first retrieval and structured extraction for legal and "
            "real-asset documents."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.config = config

    cors_origins = config.cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_route.router)
    app.include_router(search_route.router)
    app.include_router(extract_route.router)
    app.include_router(documents_route.router)

    return app
