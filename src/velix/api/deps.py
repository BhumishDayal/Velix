"""Dependency injection wiring for the FastAPI app.

The "real" implementations (ColQwen2 embedder, Qwen2.5-VL extractor, file-
backed Qdrant) are GPU-bound. The "mock" implementations are CPU-only and
used by tests + local dev. Both implement the same interfaces so route
handlers don't care which is plugged in.

Singletons live on ``app.state``. Tests can override them by replacing the
attribute directly or via FastAPI dependency overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from velix.extraction import Extractor, MockExtractor
from velix.retrieval import Embedder, MockEmbedder, VelixIndex
from velix.retrieval.index import make_qdrant_client

from .cache import ExtractionCache
from .document_store import DocumentStore


@dataclass
class AppConfig:
    """Where to load corpora, where Qdrant lives, where the cache file goes."""

    manifest_paths: list[Path]
    qdrant_target: str = "memory"
    cache_db_path: Path = Path("velix_api_cache.sqlite")
    use_mock_embedder: bool = True
    use_mock_extractor: bool = True
    cors_origins: list[str] | None = None
    require_pdf: bool = False


def build_embedder(config: AppConfig) -> Embedder:
    if config.use_mock_embedder:
        return MockEmbedder()
    from velix.retrieval.embedder import ColQwen2Embedder

    return ColQwen2Embedder()


def build_extractor(config: AppConfig) -> Extractor:
    if config.use_mock_extractor:
        return MockExtractor()
    from velix.extraction.extractor import Qwen2VLExtractor

    return Qwen2VLExtractor()


def build_index(config: AppConfig, embedder: Embedder) -> VelixIndex:
    client = make_qdrant_client(config.qdrant_target)
    return VelixIndex(client, embedding_dim=embedder.embedding_dim)


def build_document_store(config: AppConfig) -> DocumentStore:
    return DocumentStore.from_manifests(
        config.manifest_paths, require_pdf=config.require_pdf
    )


# ─────────────────────────────────────────────────────────────────────────
# FastAPI dependency callables — pull singletons off request.app.state.
# ─────────────────────────────────────────────────────────────────────────


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder


def get_extractor(request: Request) -> Extractor:
    return request.app.state.extractor


def get_index(request: Request) -> VelixIndex:
    return request.app.state.index


def get_document_store(request: Request) -> DocumentStore:
    return request.app.state.documents


def get_cache(request: Request) -> ExtractionCache:
    return request.app.state.cache


# Convenience aliases for route signatures
ConfigDep = Annotated[AppConfig, Depends(get_config)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
ExtractorDep = Annotated[Extractor, Depends(get_extractor)]
IndexDep = Annotated[VelixIndex, Depends(get_index)]
DocumentStoreDep = Annotated[DocumentStore, Depends(get_document_store)]
CacheDep = Annotated[ExtractionCache, Depends(get_cache)]
