from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from velix.extraction import DOC_TYPE_REGISTRY
from velix.extraction.schemas import BaseExtraction
from velix.retrieval.page_rendering import render_pdf_pages

from ..deps import CacheDep, DocumentStoreDep, ExtractorDep

router = APIRouter(tags=["extract"])


_BASE_FIELDS = set(BaseExtraction.model_fields.keys())


def _compute_missing_fields(instance: BaseExtraction) -> list[str]:
    missing: list[str] = []
    for name in instance.__class__.model_fields:
        if name in _BASE_FIELDS:
            continue
        value = getattr(instance, name)
        if value is None or value == [] or value == "":
            missing.append(name)
    return missing


class ExtractRequest(BaseModel):
    source: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    page_number: int = Field(ge=0)
    schema_name: str = Field(min_length=1)


class ExtractResponse(BaseModel):
    source: str
    source_id: str
    page_number: int
    schema_name: str
    cached: bool
    extraction: dict[str, Any]


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    body: ExtractRequest,
    documents: DocumentStoreDep,
    extractor: ExtractorDep,
    cache: CacheDep,
    refresh: Annotated[bool, Query()] = False,
) -> ExtractResponse:
    schema_class = DOC_TYPE_REGISTRY.get(body.schema_name)
    if schema_class is None:
        raise HTTPException(
            status_code=400,
            detail=f"unknown schema_name '{body.schema_name}'. "
            f"choices: {sorted(DOC_TYPE_REGISTRY)}",
        )

    record = documents.get(body.source, body.source_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"document not found: {body.source}/{body.source_id}",
        )

    if not refresh:
        cached = await cache.get(
            body.source, body.source_id, body.page_number, body.schema_name
        )
        if cached is not None:
            return ExtractResponse(
                source=body.source,
                source_id=body.source_id,
                page_number=body.page_number,
                schema_name=body.schema_name,
                cached=True,
                extraction=cached,
            )

    if not record.file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF not available on disk: {record.file_path}",
        )

    target_image = None
    for page_number, image in render_pdf_pages(record.file_path):
        if page_number == body.page_number:
            target_image = image
            break
    if target_image is None:
        raise HTTPException(
            status_code=404,
            detail=f"page {body.page_number} not found in {record.source_id} "
            f"(doc has {record.page_count} pages)",
        )

    try:
        instance = extractor.extract(
            target_image, schema_class, page_number=body.page_number
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "model output failed schema validation", "errors": exc.errors()},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    missing = _compute_missing_fields(instance)
    if missing and not instance.missing_fields:
        instance = instance.model_copy(update={"missing_fields": missing})
    payload = instance.model_dump(mode="json")
    await cache.set(
        body.source, body.source_id, body.page_number, body.schema_name, payload
    )
    return ExtractResponse(
        source=body.source,
        source_id=body.source_id,
        page_number=body.page_number,
        schema_name=body.schema_name,
        cached=False,
        extraction=payload,
    )
