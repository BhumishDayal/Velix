"""Confidence-gated tier-routing orchestrator."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

from velix.config import settings
from velix.models import DocumentExtraction, PageExtraction, Tier
from velix.pipeline.base import TierExtractor
from velix.pipeline.tier0_pdf import Tier0TextLayerProbe
from velix.pipeline.tier1_paddle import Tier1PaddleOCR
from velix.pipeline.tier2_olmocr import Tier2OlmOCR
from velix.pipeline.tier3_claude import Tier3ClaudeVision


class Pipeline:
    def __init__(
        self,
        tier0: TierExtractor | None = None,
        tier1: TierExtractor | None = None,
        tier2: TierExtractor | None = None,
        tier3: TierExtractor | None = None,
        tier1_threshold: float | None = None,
        tier2_threshold: float | None = None,
        tier3_threshold: float | None = None,
        enable_tier3: bool | None = None,
    ) -> None:
        self.tier0 = tier0 or Tier0TextLayerProbe()
        self.tier1 = tier1 or Tier1PaddleOCR()
        self.tier2 = tier2 or Tier2OlmOCR()
        self.tier3 = tier3 or Tier3ClaudeVision()
        self.tier1_threshold = (
            tier1_threshold
            if tier1_threshold is not None
            else settings.tier1_confidence_threshold
        )
        self.tier2_threshold = (
            tier2_threshold
            if tier2_threshold is not None
            else settings.tier2_confidence_threshold
        )
        self.tier3_threshold = (
            tier3_threshold
            if tier3_threshold is not None
            else settings.tier3_confidence_threshold
        )
        self.enable_tier3 = (
            enable_tier3 if enable_tier3 is not None else settings.tier3_enabled
        )

    def run(self, pdf_path: str | Path) -> DocumentExtraction:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        with pymupdf.open(pdf_path) as doc:
            page_count = doc.page_count

        document = DocumentExtraction(
            document_id=str(uuid.uuid4()),
            source_path=str(pdf_path),
            page_count=page_count,
        )

        tiers_used: set[Tier] = set()
        for page_number in range(page_count):
            page_extraction = self._extract_page_with_routing(pdf_path, page_number)
            document.pages.append(page_extraction)
            document.total_cost_usd += page_extraction.cost_usd
            tiers_used.add(page_extraction.tier)

        document.tiers_used = sorted(tiers_used, key=lambda t: t.value)
        document.finished_at = datetime.now(timezone.utc)
        return document

    def _extract_page_with_routing(
        self, pdf_path: Path, page_number: int
    ) -> PageExtraction:
        result = self.tier0.extract_page(pdf_path, page_number)
        if result.confidence >= self.tier1_threshold:
            return result

        if self.tier1.is_available():
            tier1_result = self.tier1.extract_page(pdf_path, page_number)
            tier1_result = self._merge_notes(tier1_result, result)
            if tier1_result.confidence >= self.tier2_threshold:
                return tier1_result
            result = tier1_result

        if self.tier2.is_available():
            tier2_result = self.tier2.extract_page(pdf_path, page_number)
            tier2_result = self._merge_notes(tier2_result, result)
            if tier2_result.confidence >= self.tier2_threshold:
                return tier2_result
            result = tier2_result

        if (
            self.enable_tier3
            and self.tier3.is_available()
            and result.confidence < self.tier3_threshold
        ):
            tier3_result = self.tier3.extract_page(pdf_path, page_number)
            return self._merge_notes(tier3_result, result)

        return result

    @staticmethod
    def _merge_notes(
        current: PageExtraction, previous: PageExtraction
    ) -> PageExtraction:
        if previous.tier == current.tier:
            return current
        prefix = f"escalated from {previous.tier.value} (conf={previous.confidence:.2f})"
        merged_notes = [prefix, *current.notes]
        return current.model_copy(update={"notes": merged_notes})
