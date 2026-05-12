"""GET /search — visual late-interaction search over the indexed corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import pymupdf
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..deps import DocumentStoreDep, EmbedderDep, IndexDep
from ..document_store import _url_safe_source_id

router = APIRouter(tags=["search"])


def _extract_page_text(pdf_path: Path, page_number: int) -> str:
    """Pull the text layer of a single page. Returns empty string for
    scanned PDFs (no text layer) or any pymupdf failure."""
    try:
        with pymupdf.open(pdf_path) as doc:
            if page_number < 0 or page_number >= doc.page_count:
                return ""
            return doc.load_page(page_number).get_text() or ""
    except Exception:
        return ""


def _make_snippet(text: str, query: str, max_len: int = 260) -> str:
    """Slice a window around the earliest query-keyword hit.

    Falls back to the start of the page when no keyword is found.
    Whitespace is collapsed so the snippet renders cleanly.
    """
    if not text or not text.strip():
        return ""
    lower = text.lower()
    keywords = [w for w in query.lower().split() if len(w) > 2]
    earliest = -1
    for word in keywords:
        idx = lower.find(word)
        if idx >= 0 and (earliest < 0 or idx < earliest):
            earliest = idx
    if earliest < 0:
        snippet = text[:max_len].strip()
        if len(text) > max_len:
            snippet += "…"
    else:
        start = max(0, earliest - 60)
        end = min(len(text), earliest + max_len - 60)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet += "…"
    return " ".join(snippet.split())


class SearchHitOut(BaseModel):
    score: float
    source: str
    source_id: str
    page_number: int
    file_path: str
    title: str
    snippet: str = ""


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
    documents: DocumentStoreDep,
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

    out: list[SearchHitOut] = []
    for hit in hits:
        # Pull a text snippet from the matched page using pymupdf's text
        # layer (Tier 0 in our pipeline). Returns "" for scanned PDFs.
        record = documents.get(hit.source, _url_safe_source_id(hit.source_id))
        snippet = ""
        if record and record.file_path.exists():
            text = _extract_page_text(record.file_path, hit.page_number)
            snippet = _make_snippet(text, q)
        out.append(
            SearchHitOut(
                score=hit.score,
                source=hit.source,
                source_id=_url_safe_source_id(hit.source_id),
                page_number=hit.page_number,
                file_path=hit.file_path,
                title=hit.title,
                snippet=snippet,
            )
        )

    return SearchResponse(
        query=q,
        limit=limit,
        source_filter=source,
        source_id_filter=source_id,
        hits=out,
    )
