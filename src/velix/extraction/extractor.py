from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date

from PIL import Image

from .schemas import (
    Assignment,
    BaseExtraction,
    DivisionOrder,
    ExtractedMineralFraction,
    ExtractedPLSSDescription,
    JointOperatingAgreement,
    MineralDeed,
    OilGasLease,
    PartyName,
    Ratification,
    RecordingInfo,
)


class Extractor(ABC):
    @abstractmethod
    def extract(
        self,
        image: Image.Image,
        schema_class: type[BaseExtraction],
        *,
        page_number: int = 0,
    ) -> BaseExtraction: ...


def _canned_for(schema_class: type[BaseExtraction], page_number: int) -> BaseExtraction:
    common = dict(page_number=page_number, extraction_confidence=0.92)

    if schema_class is MineralDeed:
        return MineralDeed(
            **common,
            grantor=PartyName(full_name="Smith Family Trust", entity_type="trust"),
            grantee=PartyName(full_name="ABC Minerals LLC", entity_type="llc"),
            fraction=ExtractedMineralFraction(
                raw_text="1/64",
                numerator=1,
                denominator=64,
                decimal_value=0.015625,
                is_power_of_two_denominator=True,
            ),
            legal_description=ExtractedPLSSDescription(
                raw_text="NE/4 of SE/4 Section 14, T2N, R3W",
                section=14,
                township_number=2,
                township_direction="N",
                range_number=3,
                range_direction="W",
                aliquots=["NE/4", "SE/4"],
            ),
            effective_date=date(2024, 6, 1),
            recording=RecordingInfo(county="Reeves", state="TX", book="412", page="88"),
        )

    if schema_class is OilGasLease:
        return OilGasLease(
            **common,
            lessor=PartyName(full_name="John Doe", entity_type="individual"),
            lessee=PartyName(full_name="Permian Basin Holdings LP", entity_type="lp"),
            royalty_fraction=ExtractedMineralFraction(
                raw_text="1/8",
                numerator=1,
                denominator=8,
                decimal_value=0.125,
                is_power_of_two_denominator=True,
            ),
            primary_term_years=5,
            legal_description=ExtractedPLSSDescription(
                raw_text="Section 22, T1S, R5E",
                section=22,
                township_number=1,
                township_direction="S",
                range_number=5,
                range_direction="E",
                aliquots=[],
            ),
            effective_date=date(2024, 9, 15),
        )

    if schema_class is DivisionOrder:
        return DivisionOrder(
            **common,
            operator=PartyName(full_name="XYZ Energy Corp", entity_type="corporation"),
            well_name="Smith #3H",
            party=PartyName(full_name="ABC Minerals LLC", entity_type="llc"),
            decimal_interest=0.015625,
            effective_date=date(2024, 6, 15),
        )

    if schema_class is Assignment:
        return Assignment(
            **common,
            assignor=PartyName(full_name="ABC Minerals LLC", entity_type="llc"),
            assignee=PartyName(full_name="DEF Royalty Partners", entity_type="partnership"),
            fraction_assigned=ExtractedMineralFraction(
                raw_text="1/32",
                numerator=1,
                denominator=32,
                decimal_value=0.03125,
                is_power_of_two_denominator=True,
            ),
            original_lease_reference="Smith-Doe Lease, Book 412 Page 88",
            effective_date=date(2024, 8, 1),
        )

    if schema_class is Ratification:
        return Ratification(
            **common,
            party=PartyName(full_name="John Doe", entity_type="individual"),
            original_document_reference="Smith-Doe Lease, Book 412 Page 88",
            ratification_date=date(2024, 10, 1),
        )

    if schema_class is JointOperatingAgreement:
        return JointOperatingAgreement(
            **common,
            operator=PartyName(full_name="XYZ Energy Corp", entity_type="corporation"),
            non_operators=[
                PartyName(full_name="ABC Minerals LLC", entity_type="llc"),
                PartyName(full_name="Permian Basin Holdings LP", entity_type="lp"),
            ],
            afe_threshold_usd=50_000.0,
            voting_threshold_pct=51.0,
        )

    raise ValueError(f"no canned instance defined for {schema_class.__name__}")


class MockExtractor(Extractor):
    """Deterministic canned-output extractor for CPU tests."""

    def extract(
        self,
        image: Image.Image,
        schema_class: type[BaseExtraction],
        *,
        page_number: int = 0,
    ) -> BaseExtraction:
        return _canned_for(schema_class, page_number)


class Qwen2VLExtractor(Extractor):
    """Qwen2.5-VL-7B with strict JSON-mode output. GPU required."""

    DEFAULT_PROMPT = (
        "You are an expert oil & gas paralegal. Read the document image and "
        "extract its fields into JSON matching this schema exactly:\n\n"
        "{schema_json}\n\n"
        "Rules:\n"
        "- Output ONLY a valid JSON object, no prose, no markdown code fences.\n"
        "- Do not invent fields not present in the document.\n"
        "- For dates use ISO 8601 (YYYY-MM-DD) or null if absent.\n"
        "- For fractions, fill numerator + denominator + decimal_value + "
        "  is_power_of_two_denominator. Power-of-two means denominators like "
        "  2, 4, 8, 16, 32, 64, 128.\n"
        "- For PLSS descriptions, township_direction is N or S; range_direction "
        "  is E or W; section is 1-36.\n"
        "- If a required field cannot be extracted with confidence, lower the "
        "  extraction_confidence score; do not guess values."
    )

    def __init__(
        self,
        *,
        model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct",
        device: str = "cuda",
        dtype: str = "bfloat16",
        max_new_tokens: int = 1024,
    ) -> None:
        import torch
        from transformers import (
            AutoProcessor,
            Qwen2_5_VLForConditionalGeneration,
        )

        torch_dtype = getattr(torch, dtype)
        self._torch = torch
        self._device = device
        self._max_new_tokens = max_new_tokens
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name, torch_dtype=torch_dtype, device_map=device
        ).eval()
        self.processor = AutoProcessor.from_pretrained(model_name)

    def extract(
        self,
        image: Image.Image,
        schema_class: type[BaseExtraction],
        *,
        page_number: int = 0,
    ) -> BaseExtraction:
        torch = self._torch
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        prompt_text = self.DEFAULT_PROMPT.format(schema_json=schema_json)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[text], images=[image], return_tensors="pt"
        ).to(self._device)

        with torch.no_grad():
            generated = self.model.generate(
                **inputs, max_new_tokens=self._max_new_tokens
            )
        trimmed = generated[:, inputs.input_ids.shape[1]:]
        output_text = self.processor.batch_decode(
            trimmed, skip_special_tokens=True
        )[0].strip()

        # Trim accidental code fences if the model emits them despite the prompt.
        if output_text.startswith("```"):
            output_text = output_text.strip("`")
            if output_text.startswith("json"):
                output_text = output_text[4:]
            output_text = output_text.strip()

        payload = json.loads(output_text)
        payload.setdefault("page_number", page_number)
        return schema_class.model_validate(payload)
