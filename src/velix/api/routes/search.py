"""GET /search — visual late-interaction search over the indexed corpus."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..deps import EmbedderDep, IndexDep

router = APIRouter(tags=["search"])


class SearchHitOut(BaseModel):
    score: float
    source: str
    source_id: str
    page_number: int
    file_path: str
    title: str


class SearchResponse(BaseModel):
    query: str
    limit: int
    source_filter: str | None = None
    hits: list[SearchHitOut]


@router.get("/search", response_model=SearchResponse)
def search(
    embedder: EmbedderDep,
    index: IndexDep,
    q: Annotated[str, Query(min_length=1, description="Natural-language query")],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    source: Annotated[str | None, Query(description="Filter to one corpus source")] = None,
) -> SearchResponse:
    query_embedding = embedder.embed_query(q)
    hits = index.search(query_embedding, limit=limit, source_filter=source)
    return SearchResponse(
        query=q,
        limit=limit,
        source_filter=source,
        hits=[
            SearchHitOut(
                score=hit.score,
                source=hit.source,
                source_id=hit.source_id,
                page_number=hit.page_number,
                file_path=hit.file_path,
                title=hit.title,
            )
            for hit in hits
        ],
    )
