"""GET /documents — list and inspect what's in the indexed corpus.

Three endpoints:
  GET /documents                       paginated list, optional source filter
  GET /documents/{source}/{source_id}  single document metadata
  GET /documents/{source}/{source_id}/pdf  stream the source PDF
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..deps import DocumentStoreDep

router = APIRouter(tags=["documents"])


class DocumentOut(BaseModel):
    source: str
    source_id: str
    page_count: int
    sha256: str
    title: str
    metadata: dict[str, Any]


class DocumentListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    source_filter: str | None
    documents: list[DocumentOut]


def _to_out(record: object) -> DocumentOut:
    return DocumentOut(
        source=record.source,  # type: ignore[attr-defined]
        source_id=record.source_id,  # type: ignore[attr-defined]
        page_count=record.page_count,  # type: ignore[attr-defined]
        sha256=record.sha256,  # type: ignore[attr-defined]
        title=record.title,  # type: ignore[attr-defined]
        metadata=record.metadata,  # type: ignore[attr-defined]
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    documents: DocumentStoreDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    source: Annotated[str | None, Query(description="Filter to one corpus source")] = None,
) -> DocumentListResponse:
    records = documents.all(source=source, offset=offset, limit=limit)
    return DocumentListResponse(
        total=len(documents),
        offset=offset,
        limit=limit,
        source_filter=source,
        documents=[_to_out(r) for r in records],
    )


@router.get("/documents/{source}/{source_id}", response_model=DocumentOut)
def get_document(
    source: str, source_id: str, documents: DocumentStoreDep
) -> DocumentOut:
    record = documents.get(source, source_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"document not found: {source}/{source_id}"
        )
    return _to_out(record)


@router.get("/documents/{source}/{source_id}/pdf")
def get_document_pdf(
    source: str, source_id: str, documents: DocumentStoreDep
) -> FileResponse:
    record = documents.get(source, source_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"document not found: {source}/{source_id}"
        )
    if not record.file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF not available on disk: {record.file_path}",
        )
    return FileResponse(
        path=record.file_path,
        media_type="application/pdf",
        filename=f"{record.source}-{record.source_id}.pdf",
    )
