"""Parser for U.S. Public Land Survey System (PLSS) legal land descriptions.

Examples we accept:
    "NE/4 of SE/4, Section 12, Township 5 North, Range 7 West"
    "N/2 SW/4 NE/4 Sec. 12, T5N, R7W"
    "the Northeast Quarter of the Southwest Quarter, Section 3, T2S, R4E, 6th P.M."

Even one bad parse in a million pages becomes a title chain we can't trust,
so we are strict about what we'll claim is valid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VALID_QUARTERS = {"NE", "NW", "SE", "SW", "N", "S", "E", "W"}
VALID_HALVES = {"N", "S", "E", "W"}

QUARTER_WORD_TO_CODE = {
    "northeast": "NE",
    "northwest": "NW",
    "southeast": "SE",
    "southwest": "SW",
    "north": "N",
    "south": "S",
    "east": "E",
    "west": "W",
}

_SECTION_RE = re.compile(
    r"\b(?:section|sec\.?)\s+(\d{1,2})\b",
    re.IGNORECASE,
)

_TOWNSHIP_RE = re.compile(
    r"\b(?:township|t\.?)\s*(\d{1,3})\s*(north|south|n|s)\b",
    re.IGNORECASE,
)

_RANGE_RE = re.compile(
    r"\b(?:range|r\.?)\s*(\d{1,3})\s*(east|west|e|w)\b",
    re.IGNORECASE,
)

_QUARTER_FRACTION_RE = re.compile(
    r"\b(N|S|E|W|NE|NW|SE|SW)\s*[/]\s*([2-4])\b",
    re.IGNORECASE,
)

_QUARTER_WORD_RE = re.compile(
    r"\b(?:the\s+)?(northeast|northwest|southeast|southwest|north|south|east|west)\s+(?:quarter|half)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LandDescription:
    section: int
    township_number: int
    township_dir: str
    range_number: int
    range_dir: str
    aliquots: tuple[str, ...]
    raw: str

    def __str__(self) -> str:
        aliquot_str = " ".join(self.aliquots) if self.aliquots else ""
        return (
            f"{aliquot_str} Sec {self.section}, "
            f"T{self.township_number}{self.township_dir}, "
            f"R{self.range_number}{self.range_dir}"
        ).strip()


def _normalize_dir(token: str) -> str:
    token = token.lower().strip()
    if token in ("n", "north"):
        return "N"
    if token in ("s", "south"):
        return "S"
    if token in ("e", "east"):
        return "E"
    if token in ("w", "west"):
        return "W"
    raise ValueError(f"Unknown direction token: {token!r}")


def _extract_aliquots(text: str) -> list[str]:
    """Pull aliquot parts (NE/4, SW/4, N/2 etc.) in left-to-right order."""

    aliquots: list[tuple[int, str]] = []

    for match in _QUARTER_FRACTION_RE.finditer(text):
        prefix, denominator = match.group(1).upper(), match.group(2)
        if denominator == "4" and prefix not in VALID_QUARTERS:
            continue
        if denominator == "2" and prefix not in VALID_HALVES:
            continue
        aliquots.append((match.start(), f"{prefix}/{denominator}"))

    for match in _QUARTER_WORD_RE.finditer(text):
        word = match.group(1).lower()
        code = QUARTER_WORD_TO_CODE[word]
        denominator = "4" if "quarter" in match.group(0).lower() else "2"
        if denominator == "4" and code not in VALID_QUARTERS:
            continue
        if denominator == "2" and code not in VALID_HALVES:
            continue
        aliquots.append((match.start(), f"{code}/{denominator}"))

    aliquots.sort(key=lambda item: item[0])
    return [code for _, code in aliquots]


def parse_land_description(text: str) -> LandDescription | None:
    """Best-effort PLSS parser. Returns None when required parts are missing."""

    section_match = _SECTION_RE.search(text)
    township_match = _TOWNSHIP_RE.search(text)
    range_match = _RANGE_RE.search(text)

    if not (section_match and township_match and range_match):
        return None

    section_num = int(section_match.group(1))
    if not 1 <= section_num <= 36:
        return None

    township_num = int(township_match.group(1))
    range_num = int(range_match.group(1))
    if township_num <= 0 or range_num <= 0:
        return None

    try:
        township_dir = _normalize_dir(township_match.group(2))
        range_dir = _normalize_dir(range_match.group(2))
    except ValueError:
        return None

    if township_dir not in {"N", "S"} or range_dir not in {"E", "W"}:
        return None

    aliquots = _extract_aliquots(text)

    return LandDescription(
        section=section_num,
        township_number=township_num,
        township_dir=township_dir,
        range_number=range_num,
        range_dir=range_dir,
        aliquots=tuple(aliquots),
        raw=text.strip(),
    )
