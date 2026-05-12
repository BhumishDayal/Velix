"""Pydantic schemas for the six oil & gas document types Velix extracts."""

from __future__ import annotations

from datetime import date
from fractions import Fraction
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from velix.validators import (
    parse_land_description,
    parse_mineral_fraction,
)


EntityType = Literal[
    "individual", "trust", "estate", "llc", "corporation",
    "partnership", "lp", "lllp", "company", "unknown",
]


class PartyName(BaseModel):
    full_name: str = Field(min_length=1)
    entity_type: EntityType = "unknown"


class ExtractedMineralFraction(BaseModel):
    raw_text: str
    numerator: int = Field(gt=0)
    denominator: int = Field(gt=0)
    decimal_value: float = Field(ge=0.0, le=1.0)
    is_power_of_two_denominator: bool

    @classmethod
    def from_text(cls, text: str) -> ExtractedMineralFraction:
        parsed = parse_mineral_fraction(text)
        if parsed is None:
            raise ValueError(f"could not parse mineral fraction from: {text!r}")
        return cls(
            raw_text=text,
            numerator=parsed.fraction.numerator,
            denominator=parsed.fraction.denominator,
            decimal_value=parsed.decimal,
            is_power_of_two_denominator=parsed.is_power_of_two_denominator,
        )

    def as_fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)


PLSSDirection = Literal["N", "S", "E", "W"]


class ExtractedPLSSDescription(BaseModel):
    raw_text: str
    section: int = Field(ge=1, le=36)
    township_number: int = Field(gt=0)
    township_direction: Literal["N", "S"]
    range_number: int = Field(gt=0)
    range_direction: Literal["E", "W"]
    aliquots: list[str] = Field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> ExtractedPLSSDescription:
        parsed = parse_land_description(text)
        if parsed is None:
            raise ValueError(f"could not parse PLSS description from: {text!r}")
        return cls(
            raw_text=text,
            section=parsed.section,
            township_number=parsed.township_number,
            township_direction=parsed.township_dir,  # type: ignore[arg-type]
            range_number=parsed.range_number,
            range_direction=parsed.range_dir,  # type: ignore[arg-type]
            aliquots=list(parsed.aliquots),
        )


class RecordingInfo(BaseModel):
    county: str
    state: str = Field(min_length=2, max_length=2)
    book: str | None = None
    page: str | None = None
    instrument_number: str | None = None


class BaseExtraction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page_number: int = Field(ge=0)
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)

    document_type: ClassVar[str]


class MineralDeed(BaseExtraction):
    document_type: Literal["mineral_deed"] = "mineral_deed"
    grantor: PartyName
    grantee: PartyName
    fraction: ExtractedMineralFraction
    legal_description: ExtractedPLSSDescription
    effective_date: date | None = None
    recording: RecordingInfo | None = None


class OilGasLease(BaseExtraction):
    document_type: Literal["oil_gas_lease"] = "oil_gas_lease"
    lessor: PartyName
    lessee: PartyName
    royalty_fraction: ExtractedMineralFraction
    primary_term_years: int = Field(gt=0, le=99)
    legal_description: ExtractedPLSSDescription
    effective_date: date | None = None
    recording: RecordingInfo | None = None


class DivisionOrder(BaseExtraction):
    document_type: Literal["division_order"] = "division_order"
    operator: PartyName
    well_name: str = Field(min_length=1)
    party: PartyName
    decimal_interest: float = Field(ge=0.0, le=1.0)
    effective_date: date | None = None


class Assignment(BaseExtraction):
    document_type: Literal["assignment"] = "assignment"
    assignor: PartyName
    assignee: PartyName
    fraction_assigned: ExtractedMineralFraction
    original_lease_reference: str | None = None
    effective_date: date | None = None


class Ratification(BaseExtraction):
    document_type: Literal["ratification"] = "ratification"
    party: PartyName
    original_document_reference: str = Field(min_length=1)
    ratification_date: date | None = None


class JointOperatingAgreement(BaseExtraction):
    document_type: Literal["joa_snippet"] = "joa_snippet"
    operator: PartyName
    non_operators: list[PartyName] = Field(min_length=1)
    afe_threshold_usd: float | None = Field(default=None, ge=0.0)
    voting_threshold_pct: float | None = Field(default=None, ge=0.0, le=100.0)


DOC_TYPE_REGISTRY: dict[str, type[BaseExtraction]] = {
    "mineral_deed": MineralDeed,
    "oil_gas_lease": OilGasLease,
    "division_order": DivisionOrder,
    "assignment": Assignment,
    "ratification": Ratification,
    "joa_snippet": JointOperatingAgreement,
}
