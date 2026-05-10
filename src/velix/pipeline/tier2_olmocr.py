"""Tier 2: olmOCR 2 self-hosted vision-language model.

olmOCR 2 (Allen AI, Apache 2.0) is built on Qwen2.5-VL-7B and was fine-tuned
on 270k pages including legal documents. Benchmarked at 82.4 on olmOCR-Bench,
beating Marker (76.1) and MinerU (75.8). On a single H100 it produces
high-quality plain text at roughly $176 per million pages.

We invoke it via Hugging Face transformers. The model weights and torch are
heavy optional dependencies; this module only imports them inside
`_load_model` so the rest of the pipeline runs on CPU-only machines.
"""

from __future__ import annotations

import time
from pathlib import Path

from velix.config import settings
from velix.models import PageExtraction, Tier
from velix.pipeline.base import TierExtractor
from velix.pipeline.rendering import render_page_to_pil

OLMOCR_PROMPT = (
    "Below is the image of one page of a document. "
    "Just return the plain text representation of this document as if you were reading it naturally. "
    "Convert equations to LaTeX and tables to markdown. "
    "Return your output as plain text without any wrapper such as ```."
)


class Tier2OlmOCR(TierExtractor):
    tier = Tier.TIER2_OLMOCR

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        max_new_tokens: int = 4096,
        dpi: int = 200,
        cost_per_page_usd: float = 0.000176,
    ) -> None:
        self.model_name = model_name or settings.tier2_olmocr_model
        self.device = device or settings.tier2_olmocr_device
        self.max_new_tokens = max_new_tokens
        self.dpi = dpi
        self.cost_per_page_usd = cost_per_page_usd
        self._model = None
        self._processor = None

    def is_available(self) -> bool:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError:
            return False
        return True

    def _load_model(self) -> None:
        if self._model is not None:
            return

        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32

        self._processor = AutoProcessor.from_pretrained(self.model_name)
        self._model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map=self.device,
        )
        self._model.eval()

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
                    "olmOCR not installed; pip install velix[olmocr]",
                ],
            )

        try:
            image = render_page_to_pil(pdf_path, page_number, dpi=self.dpi)
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
            self._load_model()
            text = self._infer(image)
        except Exception as exc:
            return PageExtraction(
                page_number=page_number,
                tier=self.tier,
                raw_text="",
                confidence=0.0,
                duration_ms=int((time.perf_counter() - start) * 1000),
                notes=[f"olmOCR inference failed: {exc}"],
            )

        confidence = self._score_output(text)
        return PageExtraction(
            page_number=page_number,
            tier=self.tier,
            raw_text=text,
            confidence=confidence,
            duration_ms=int((time.perf_counter() - start) * 1000),
            cost_usd=self.cost_per_page_usd,
            notes=[f"{len(text)} chars, model={self.model_name}"],
        )

    def _infer(self, image) -> str:
        import torch

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": OLMOCR_PROMPT},
                ],
            }
        ]
        prompt = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(
            text=[prompt],
            images=[image],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        generated = output_ids[:, inputs.input_ids.shape[1]:]
        decoded = self._processor.batch_decode(
            generated, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return decoded[0].strip() if decoded else ""

    @staticmethod
    def _score_output(text: str) -> float:
        if not text:
            return 0.0
        if len(text) < 30:
            return 0.4
        if len(text) < 150:
            return 0.75
        return 0.95
