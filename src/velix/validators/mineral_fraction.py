"""Parser for mineral interest fractions found in oil & gas conveyances.

Mineral interests are routinely written as 1/64, 5/192, 3/16, etc., and
silent OCR errors here corrupt royalty math. This module reduces the fraction
and flags non-power-of-two denominators that frequently indicate misreads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

_FRACTION_RE = re.compile(r"\b(\d{1,5})\s*/\s*(\d{1,5})\b")

_DECIMAL_RE = re.compile(r"\b0?\.\d{2,12}\b")

_WORD_FRACTIONS = {
    "one half": Fraction(1, 2),
    "one third": Fraction(1, 3),
    "one quarter": Fraction(1, 4),
    "one fourth": Fraction(1, 4),
    "one eighth": Fraction(1, 8),
    "one sixteenth": Fraction(1, 16),
    "one thirty-second": Fraction(1, 32),
    "one sixty-fourth": Fraction(1, 64),
    "one one-hundred-twenty-eighth": Fraction(1, 128),
    "one ninety-second": Fraction(1, 92),
}


@dataclass(frozen=True)
class MineralFraction:
    raw: str
    fraction: Fraction
    is_power_of_two_denominator: bool
    decimal: float

    @property
    def reduced(self) -> str:
        return f"{self.fraction.numerator}/{self.fraction.denominator}"


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def parse_mineral_fraction(text: str) -> MineralFraction | None:
    text = text.strip()

    fraction_match = _FRACTION_RE.search(text)
    if fraction_match:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))
        if denominator == 0:
            return None
        if numerator > denominator:
            return None
        frac = Fraction(numerator, denominator)
        return MineralFraction(
            raw=text,
            fraction=frac,
            is_power_of_two_denominator=_is_power_of_two(frac.denominator),
            decimal=float(frac),
        )

    decimal_match = _DECIMAL_RE.search(text)
    if decimal_match:
        try:
            decimal_value = float(decimal_match.group(0))
        except ValueError:
            return None
        if not 0 < decimal_value <= 1:
            return None
        frac = Fraction(decimal_value).limit_denominator(4096)
        return MineralFraction(
            raw=text,
            fraction=frac,
            is_power_of_two_denominator=_is_power_of_two(frac.denominator),
            decimal=decimal_value,
        )

    lowered = text.lower()
    for phrase, frac in _WORD_FRACTIONS.items():
        if phrase in lowered:
            return MineralFraction(
                raw=text,
                fraction=frac,
                is_power_of_two_denominator=_is_power_of_two(frac.denominator),
                decimal=float(frac),
            )

    return None
