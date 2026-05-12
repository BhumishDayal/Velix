from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .cache import ExtractionCache
from .deps import (
    AppConfig,
    build_document_store,
    build_embedder,
    build_extractor,
    build_index,
)
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


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(title="Velix API", version="0.1.0", lifespan=lifespan)
    app.state.config = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_route.router)
    app.include_router(search_route.router)
    app.include_router(extract_route.router)
    app.include_router(documents_route.router)

    return app
