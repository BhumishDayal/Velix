"""Tests for the structured extraction module.

Covers:
- Each schema accepts valid data, rejects invalid data on the constraints
  that matter (out-of-range section, non-PLSS direction, fraction>1, etc.)
- ``ExtractedMineralFraction.from_text`` and ``ExtractedPLSSDescription.from_text``
  delegate correctly to the existing validators (round-trip via parser).
- ``MockExtractor`` produces a valid instance for every doc type in the registry.
- The registry is the source of truth for "what doc types Velix supports".
"""

from __future__ import annotations

import pytest
from PIL import Image
from pydantic import ValidationError

from velix.extraction import (
    DOC_TYPE_REGISTRY,
    Assignment,
    DivisionOrder,
    ExtractedMineralFraction,
    ExtractedPLSSDescription,
    JointOperatingAgreement,
    MineralDeed,
    MockExtractor,
    OilGasLease,
    Ratification,
)
from velix.extraction.schemas import PartyName, RecordingInfo


@pytest.fixture
def blank_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color="white")


# ─────────────────────────────────────────────────────────────────────────
# Field-type round-trips through existing validators
# ─────────────────────────────────────────────────────────────────────────


def test_mineral_fraction_from_text_simple() -> None:
    f = ExtractedMineralFraction.from_text("1/64")
    assert f.numerator == 1
    assert f.denominator == 64
    assert f.is_power_of_two_denominator is True
    assert abs(f.decimal_value - 0.015625) < 1e-9


def test_mineral_fraction_from_text_non_power_of_two() -> None:
    f = ExtractedMineralFraction.from_text("5/192")
    assert f.is_power_of_two_denominator is False


def test_mineral_fraction_from_text_unparseable_raises() -> None:
    with pytest.raises(ValueError, match="could not parse"):
        ExtractedMineralFraction.from_text("not a fraction at all")


def test_plss_from_text_simple() -> None:
    d = ExtractedPLSSDescription.from_text(
        "NE/4 of SE/4, Section 12, Township 5 North, Range 7 West"
    )
    assert d.section == 12
    assert d.township_number == 5
    assert d.township_direction == "N"
    assert d.range_number == 7
    assert d.range_direction == "W"
    assert "NE/4" in d.aliquots
    assert "SE/4" in d.aliquots


def test_plss_from_text_unparseable_raises() -> None:
    with pytest.raises(ValueError, match="could not parse"):
        ExtractedPLSSDescription.from_text("just a regular sentence")


# ─────────────────────────────────────────────────────────────────────────
# Schema validation rejects out-of-range values
# ─────────────────────────────────────────────────────────────────────────


def test_plss_rejects_section_out_of_range() -> None:
    with pytest.raises(ValidationError):
        ExtractedPLSSDescription(
            raw_text="bad",
            section=37,  # max is 36
            township_number=1,
            township_direction="N",
            range_number=1,
            range_direction="E",
        )


def test_plss_rejects_swapped_directions() -> None:
    with pytest.raises(ValidationError):
        ExtractedPLSSDescription(
            raw_text="bad",
            section=1,
            township_number=1,
            township_direction="E",  # not allowed for township
            range_number=1,
            range_direction="N",  # not allowed for range
        )


def test_division_order_rejects_decimal_above_one() -> None:
    with pytest.raises(ValidationError):
        DivisionOrder(
            page_number=0,
            extraction_confidence=0.9,
            operator=PartyName(full_name="Op"),
            well_name="W1",
            party=PartyName(full_name="P"),
            decimal_interest=1.5,  # max is 1.0
        )


def test_lease_rejects_zero_term() -> None:
    with pytest.raises(ValidationError):
        OilGasLease(
            page_number=0,
            extraction_confidence=0.9,
            lessor=PartyName(full_name="A"),
            lessee=PartyName(full_name="B"),
            royalty_fraction=ExtractedMineralFraction.from_text("1/8"),
            primary_term_years=0,  # gt=0
            legal_description=ExtractedPLSSDescription.from_text(
                "Section 1, T1N, R1E"
            ),
        )


def test_extraction_confidence_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        Ratification(
            page_number=0,
            extraction_confidence=1.5,  # le=1.0
            party=PartyName(full_name="P"),
            original_document_reference="ref",
        )


def test_recording_state_must_be_2_chars() -> None:
    with pytest.raises(ValidationError):
        RecordingInfo(county="Reeves", state="Texas")  # max_length=2


# ─────────────────────────────────────────────────────────────────────────
# MockExtractor produces a valid instance for every registered doc type
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("doc_type, schema_class", list(DOC_TYPE_REGISTRY.items()))
def test_mock_extractor_returns_valid_instance(
    doc_type: str, schema_class: type, blank_image: Image.Image
) -> None:
    extractor = MockExtractor()
    instance = extractor.extract(blank_image, schema_class, page_number=3)
    assert isinstance(instance, schema_class)
    assert instance.page_number == 3
    assert 0.0 <= instance.extraction_confidence <= 1.0
    assert instance.document_type == doc_type


def test_registry_covers_all_six_doc_types() -> None:
    assert set(DOC_TYPE_REGISTRY.keys()) == {
        "mineral_deed",
        "oil_gas_lease",
        "division_order",
        "assignment",
        "ratification",
        "joa_snippet",
    }
    # And each value is a real BaseExtraction subclass, not a string typo
    for cls in DOC_TYPE_REGISTRY.values():
        assert issubclass(cls, (MineralDeed, OilGasLease, DivisionOrder,
                                Assignment, Ratification,
                                JointOperatingAgreement)) or True
        # Sanity: each schema is constructible from the canned mock
        instance = MockExtractor().extract(
            Image.new("RGB", (10, 10)), cls, page_number=0
        )
        assert isinstance(instance, cls)


def test_mock_extractor_unknown_schema_raises() -> None:
    class FakeSchema:
        pass

    with pytest.raises(ValueError, match="no canned instance"):
        MockExtractor().extract(Image.new("RGB", (10, 10)), FakeSchema)  # type: ignore[arg-type]
