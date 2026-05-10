from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Tier(str, Enum):
    TIER0_PDF_TEXT = "tier0_pdf_text"
    TIER1_PADDLE = "tier1_paddle"
    TIER2_OLMOCR = "tier2_olmocr"
    TIER3_CLAUDE = "tier3_claude"


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BoundingBox(BaseModel):
    """Pixel coordinates of an extracted region within its source page."""

    x: float
    y: float
    width: float
    height: float
    page: int


class ExtractedField(BaseModel):
    """A single typed value pulled from a document with provenance."""

    name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox | None = None
    validation_status: ValidationStatus = ValidationStatus.SKIPPED
    validation_notes: list[str] = Field(default_factory=list)


class PageExtraction(BaseModel):
    """Result of running a single tier against a single page."""

    page_number: int
    tier: Tier
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    fields: list[ExtractedField] = Field(default_factory=list)
    duration_ms: int = 0
    cost_usd: float = 0.0
    notes: list[str] = Field(default_factory=list)


class DocumentExtraction(BaseModel):
    """Final aggregated result for a full document after all tier routing."""

    document_id: str
    source_path: str
    page_count: int
    pages: list[PageExtraction] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    total_cost_usd: float = 0.0
    tiers_used: list[Tier] = Field(default_factory=list)

    @property
    def overall_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.confidence for p in self.pages) / len(self.pages)
