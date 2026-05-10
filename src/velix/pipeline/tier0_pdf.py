"""Tier 0: PDF text-layer probe via pymupdf.

If the PDF was generated digitally (Word → PDF, signing platforms, modern
e-filing systems) it has a text layer that is *the source* — pulling it is
free, instant, and 100% accurate. This tier handles the bulk of modern legal
docs at zero per-page cost.

Confidence is conservative: even when text is present we sanity-check that
the page is not mostly an image with a thin caption layer (a common pattern
in scanned docs that have been "OCRed" by Acrobat with poor results).
"""

from __future__ import annotations

import time
from pathlib import Path

import pymupdf

from velix.models import PageExtraction, Tier
from velix.pipeline.base import TierExtractor


class Tier0TextLayerProbe(TierExtractor):
    tier = Tier.TIER0_PDF_TEXT

    def __init__(
        self,
        min_chars_per_page: int = 50,
        min_text_to_image_area_ratio: float = 0.05,
    ) -> None:
        self.min_chars_per_page = min_chars_per_page
        self.min_text_to_image_area_ratio = min_text_to_image_area_ratio

    def extract_page(self, pdf_path: Path, page_number: int) -> PageExtraction:
        start = time.perf_counter()

        try:
            doc = pymupdf.open(pdf_path)
        except Exception as exc:
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[f"pymupdf could not open file: {exc}"],
            )

        try:
            if page_number < 0 or page_number >= doc.page_count:
                return PageExtraction(
                    page_number=page_number,
                    tier=self.tier,
                    raw_text="",
                    confidence=0.0,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    notes=[f"page {page_number} out of range (0..{doc.page_count - 1})"],
                )

            page = doc.load_page(page_number)
            text = page.get_text("text") or ""
            confidence, notes = self._score_text_layer(page, text)

            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text=text,
                confidence=confidence,
                duration_ms=int((time.perf_counter() - start) * 1000),
                cost_usd=0.0,
                notes=notes,
            )
        finally:
            doc.close()

    def _score_text_layer(
        self, page: pymupdf.Page, text: str
    ) -> tuple[float, list[str]]:
        notes: list[str] = []
        char_count = len(text.strip())

        if char_count == 0:
            return 0.0, ["no text layer present"]

        if char_count < self.min_chars_per_page:
            notes.append(
                f"sparse text layer ({char_count} chars < {self.min_chars_per_page})"
            )
            return 0.3, notes

        page_area = max(page.rect.width * page.rect.height, 1.0)
        image_area = sum(
            (img_rect.width * img_rect.height)
            for img_rect in (
                pymupdf.Rect(item[1], item[2], item[3], item[4])
                for item in page.get_image_info(xrefs=True)
                if len(item) >= 5
            )
        )
        image_ratio = min(image_area / page_area, 1.0)

        if image_ratio > 1.0 - self.min_text_to_image_area_ratio:
            notes.append(
                f"page is mostly image ({image_ratio:.0%}); text layer may be unreliable"
            )
            return 0.5, notes

        confidence = 0.99 if char_count > 200 else 0.9
        notes.append(f"clean text layer, {char_count} chars")
        return confidence, notes
