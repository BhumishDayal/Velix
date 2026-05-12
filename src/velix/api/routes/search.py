"""GET /search — visual late-interaction search over the indexed corpus."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..deps import EmbedderDep, IndexDep
from ..document_store import _url_safe_source_id

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
    source_id_filter: str | None = None
    hits: list[SearchHitOut]


@router.get("/search", response_model=SearchResponse)
def search(
    embedder: EmbedderDep,
    index: IndexDep,
    q: Annotated[str, Query(min_length=1, description="Natural-language query")],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    source: Annotated[
        str | None, Query(description="Filter to one corpus source")
    ] = None,
    source_id: Annotated[
        str | None,
        Query(description="Filter to a single document (URL-safe source_id)"),
    ] = None,
) -> SearchResponse:
    query_embedding = embedder.embed_query(q)

    # Qdrant payload stores source_ids in raw form (with '/'); the URL-safe
    # form (with '--') incoming from the frontend has to be converted back
    # before filtering. Use the raw form on the wire if you want; both work.
    raw_source_id = (
        source_id.replace("--", "/") if source_id and "--" in source_id else source_id
    )

    hits = index.search(
        query_embedding,
        limit=limit,
        source_filter=source,
        source_id_filter=raw_source_id,
    )

    # Normalize source_ids in the response to URL-safe form so the frontend
    # can use them directly in route paths.
    return SearchResponse(
        query=q,
        limit=limit,
        source_filter=source,
        source_id_filter=source_id,
        hits=[
            SearchHitOut(
                score=hit.score,
                source=hit.source,
                source_id=_url_safe_source_id(hit.source_id),
                page_number=hit.page_number,
                file_path=hit.file_path,
                title=hit.title,
            )
            for hit in hits
        ],
    )
