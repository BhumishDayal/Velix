"""Tier 1: PaddleOCR self-hosted recognition.

Picked over Tesseract because PP-StructureV3 handles the table-heavy layouts
common in title opinions, division orders, and assignments. Per-block
confidences from PaddleOCR feed our page-level confidence so the orchestrator
can decide whether Tier 2 escalation is needed.

PaddleOCR is an optional dependency; if it is not installed, this tier
reports itself as unavailable rather than crashing imports.
"""

from __future__ import annotations

import time
from pathlib import Path

from velix.models import PageExtraction, Tier
from velix.pipeline.base import TierExtractor
from velix.pipeline.rendering import render_page_to_array


class Tier1PaddleOCR(TierExtractor):
    tier = Tier.TIER1_PADDLE

    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        dpi: int = 200,
        cost_per_page_usd: float = 0.00009,
    ) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.dpi = dpi
        self.cost_per_page_usd = cost_per_page_usd
        self._engine: object | None = None

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
        except ImportError:
            return False
        return True

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        from paddleocr import PaddleOCR

        self._engine = PaddleOCR(
            use_angle_cls=self.use_angle_cls,
            lang=self.lang,
            show_log=False,
        )
        return self._engine

    def extract_page(self, pdf_path: Path, page_number: int) -> PageExtraction:
        start = time.perf_counter()

        if not self.is_available():
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=["paddleocr not installed; pip install velix[paddle]"],
            )

        try:
            image = render_page_to_array(pdf_path, page_number, dpi=self.dpi)
        except Exception as exc:
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[f"failed to render page: {exc}"],
            )

        engine = self._get_engine()
        try:
            result = engine.ocr(image, cls=self.use_angle_cls)
        except Exception as exc:
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[f"paddleocr inference failed: {exc}"],
            )

        text, confidence, line_count = self._parse_paddle_result(result)

        notes = [f"{line_count} text lines detected"]
        if line_count == 0:
            notes.append("no text recognized; page likely empty or unreadable")

        return PageExtraction(
            page_number=page_number,
            tier=self.tier,
            raw_text=text,
            confidence=confidence,
            duration_ms=int((time.perf_counter() - start) * 1000),
            cost_usd=self.cost_per_page_usd,
            notes=notes,
        )

    @staticmethod
    def _parse_paddle_result(result) -> tuple[str, float, int]:
        if not result or not result[0]:
            return "", 0.0, 0

        lines: list[str] = []
        confidences: list[float] = []

        for line in result[0]:
            try:
                _, (text, score) = line
            except (TypeError, ValueError):
                continue
            if not text:
                continue
            lines.append(text)
            confidences.append(float(score))

        if not lines:
            return "", 0.0, 0

        joined = "\n".join(lines)
        page_confidence = sum(confidences) / len(confidences)
        return joined, page_confidence, len(lines)
