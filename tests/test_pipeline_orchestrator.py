"""Integration tests for the confidence-gated tier orchestrator.

Each test wires the Pipeline with FakeTier extractors that return canned
PageExtraction results, so escalation logic is exercised independently of
the real OCR/VLM backends.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from velix.models import PageExtraction, Tier
from velix.pipeline.base import TierExtractor
from velix.pipeline.orchestrator import Pipeline


class FakeTier(TierExtractor):
    def __init__(
        self,
        tier: Tier,
        confidence: float,
        *,
        available: bool = True,
        cost: float = 0.0,
        raw_text: str = "fake",
    ) -> None:
        self.tier = tier
        self.confidence = confidence
        self._available = available
        self.cost = cost
        self.raw_text = raw_text
        self.call_count = 0

    def extract_page(self, pdf_path: Path, page_number: int) -> PageExtraction:
        self.call_count += 1
        return PageExtraction(
            page_number=page_number,
            tier=self.tier,
            raw_text=self.raw_text,
            confidence=self.confidence,
            cost_usd=self.cost,
        )

    def is_available(self) -> bool:
        return self._available


@pytest.fixture
def two_page_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "two_page.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


def _build_pipeline(
    *,
    tier0_conf: float,
    tier1_conf: float,
    tier2_conf: float,
    tier3_conf: float = 0.97,
    tier1_available: bool = True,
    tier2_available: bool = True,
    tier3_available: bool = True,
    enable_tier3: bool = False,
) -> tuple[Pipeline, dict[str, FakeTier]]:
    tiers = {
        "tier0": FakeTier(Tier.TIER0_PDF_TEXT, tier0_conf, cost=0.0),
        "tier1": FakeTier(
            Tier.TIER1_PADDLE, tier1_conf, available=tier1_available, cost=0.0001
        ),
        "tier2": FakeTier(
            Tier.TIER2_OLMOCR, tier2_conf, available=tier2_available, cost=0.0002
        ),
        "tier3": FakeTier(
            Tier.TIER3_CLAUDE, tier3_conf, available=tier3_available, cost=0.01
        ),
    }
    pipeline = Pipeline(
        tier0=tiers["tier0"],
        tier1=tiers["tier1"],
        tier2=tiers["tier2"],
        tier3=tiers["tier3"],
        tier1_threshold=0.85,
        tier2_threshold=0.92,
        tier3_threshold=0.80,
        enable_tier3=enable_tier3,
    )
    return pipeline, tiers


def test_tier0_short_circuits_when_text_layer_strong(two_page_pdf: Path) -> None:
    pipeline, tiers = _build_pipeline(tier0_conf=0.99, tier1_conf=0.0, tier2_conf=0.0)

    document = pipeline.run(two_page_pdf)

    assert document.page_count == 2
    assert all(p.tier == Tier.TIER0_PDF_TEXT for p in document.pages)
    assert tiers["tier1"].call_count == 0
    assert tiers["tier2"].call_count == 0
    assert tiers["tier3"].call_count == 0
    assert document.total_cost_usd == 0.0


def test_escalates_through_all_tiers_when_each_fails(two_page_pdf: Path) -> None:
    pipeline, tiers = _build_pipeline(
        tier0_conf=0.10,
        tier1_conf=0.20,
        tier2_conf=0.30,
        tier3_conf=0.97,
        enable_tier3=True,
    )

    document = pipeline.run(two_page_pdf)

    assert all(p.tier == Tier.TIER3_CLAUDE for p in document.pages)
    assert tiers["tier1"].call_count == 2
    assert tiers["tier2"].call_count == 2
    assert tiers["tier3"].call_count == 2
    assert document.total_cost_usd == pytest.approx(0.02)
    # Escalation provenance should be preserved in notes.
    assert any("escalated from" in note for note in document.pages[0].notes)


def test_tier3_threshold_blocks_unnecessary_claude_escalation(two_page_pdf: Path) -> None:
    """The bug fix: when Tier 2 is below tier2_threshold but above tier3_threshold,
    accept the Tier 2 result instead of paying for Claude."""
    pipeline, tiers = _build_pipeline(
        tier0_conf=0.10,
        tier1_conf=0.20,
        tier2_conf=0.85,  # below tier2_threshold (0.92), above tier3_threshold (0.80)
        tier3_conf=0.97,
        enable_tier3=True,
    )

    document = pipeline.run(two_page_pdf)

    assert all(p.tier == Tier.TIER2_OLMOCR for p in document.pages)
    assert tiers["tier3"].call_count == 0
    assert document.total_cost_usd == pytest.approx(0.0004)


def test_tier3_disabled_returns_best_lower_tier_result(two_page_pdf: Path) -> None:
    pipeline, tiers = _build_pipeline(
        tier0_conf=0.10,
        tier1_conf=0.20,
        tier2_conf=0.30,
        enable_tier3=False,
    )

    document = pipeline.run(two_page_pdf)

    assert all(p.tier == Tier.TIER2_OLMOCR for p in document.pages)
    assert tiers["tier3"].call_count == 0


def test_skips_unavailable_tiers(two_page_pdf: Path) -> None:
    pipeline, tiers = _build_pipeline(
        tier0_conf=0.10,
        tier1_conf=0.0,
        tier2_conf=0.99,
        tier1_available=False,
        enable_tier3=False,
    )

    document = pipeline.run(two_page_pdf)

    assert all(p.tier == Tier.TIER2_OLMOCR for p in document.pages)
    assert tiers["tier1"].call_count == 0
    assert tiers["tier2"].call_count == 2


def test_missing_pdf_raises(tmp_path: Path) -> None:
    pipeline, _ = _build_pipeline(tier0_conf=0.99, tier1_conf=0.0, tier2_conf=0.0)
    with pytest.raises(FileNotFoundError):
        pipeline.run(tmp_path / "does_not_exist.pdf")
