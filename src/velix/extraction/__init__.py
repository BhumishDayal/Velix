"""On-demand structured extraction layer.

Each PDF page is processed by a vision-language model only when actually
queried — not upfront — and the model's output is constrained by a strict
Pydantic schema specific to the document type. This is the "VLM + Pydantic
replaces OCR + regex" pattern.

The existing domain validators in ``velix.validators`` (PLSS, mineral
fractions, party consistency) are wired into the schemas as field
validators rather than running as a post-hoc step.
"""

from .extractor import Extractor, MockExtractor
from .schemas import (
    DOC_TYPE_REGISTRY,
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

__all__ = [
    "Extractor",
    "MockExtractor",
    "DOC_TYPE_REGISTRY",
    "BaseExtraction",
    "PartyName",
    "ExtractedMineralFraction",
    "ExtractedPLSSDescription",
    "RecordingInfo",
    "MineralDeed",
    "OilGasLease",
    "DivisionOrder",
    "Assignment",
    "Ratification",
    "JointOperatingAgreement",
]
