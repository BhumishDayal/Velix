"""Tier 3: Claude Sonnet 4.6 vision escalation.

This is the "last 1%" tier — invoked only when Tier 2 confidence is below
threshold and the document contains a legally critical field (mineral
fraction, party name in the chain, legal land description). At ~$0.01/page
it is too expensive to run by default but cheap enough to spend on the
pages where silent OCR errors would corrupt royalty math.

The Anthropic SDK is an optional dependency.
"""

from __future__ import annotations

import base64
import time
from io import BytesIO
from pathlib import Path

from velix.config import settings
from velix.models import PageExtraction, Tier
from velix.pipeline.base import TierExtractor
from velix.pipeline.rendering import render_page_to_pil

CLAUDE_PROMPT = (
    "You are extracting text from a legal document page (oil & gas title, "
    "lease, assignment, division order, or related instrument). Return the "
    "exact verbatim text of the page in reading order. Preserve legal land "
    "descriptions (Section/Township/Range), mineral interest fractions, and "
    "party names exactly as written. Do not summarize, paraphrase, or "
    "correct apparent errors. Output only the page text — no preamble, no "
    "markdown fences, no commentary."
)


class Tier3ClaudeVision(TierExtractor):
    tier = Tier.TIER3_CLAUDE

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 8000,
        dpi: int = 200,
        cost_per_page_usd: float = 0.01,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.dpi = dpi
        self.cost_per_page_usd = cost_per_page_usd
        self.api_key = api_key or settings.anthropic_api_key
        self._client = None

    def is_available(self) -> bool:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def extract_page(self, pdf_path: Path, page_number: int) -> PageExtraction:
        start = time.perf_counter()

        if not self.is_available():
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[
                    "anthropic SDK missing or ANTHROPIC_API_KEY unset; "
                    "pip install velix[claude] and set the env var",
                ],
            )

        try:
            image = render_page_to_pil(pdf_path, page_number, dpi=self.dpi)
            buf = BytesIO()
            image.save(buf, format="PNG")
            image_b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
        except Exception as exc:
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[f"failed to render page: {exc}"],
            )

        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": CLAUDE_PROMPT},
                        ],
                    }
                ],
            )
            text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
        except Exception as exc:
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[f"Claude inference failed: {exc}"],
            )

        confidence = 0.97 if len(text) >= 30 else 0.5
        return PageExtraction(
            page_number=page_number,
            tier=self.tier,
            raw_text=text,
            confidence=confidence,
            duration_ms=int((time.perf_counter() - start) * 1000),
            cost_usd=self.cost_per_page_usd,
            notes=[f"{len(text)} chars, model={self.model}"],
        )
