from __future__ import annotations

from fastapi import APIRouter

from ..deps import CacheDep, DocumentStoreDep, IndexDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    documents: DocumentStoreDep,
    index: IndexDep,
    cache: CacheDep,
) -> dict[str, object]:
    return {
        "status": "ok",
        "documents": len(documents),
        "indexed_pages": index.count(),
        "cached_extractions": await cache.count(),
    }
