"""Cross-document grantor/grantee chain consistency checker.

For a chain of title to be sound, the grantee on document N must match the
grantor on document N+1 (give or take spelling variants, suffix changes, and
entity-name normalization). This module flags breaks before they reach a
title attorney.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]")
_WHITESPACE_RE = re.compile(r"\s+")

# token_set_ratio threshold for two normalized party names to be considered
# the same party. 85 tolerates common OCR noise (one or two character flips,
# missing/extra whitespace) without merging genuinely different parties.
NAME_MATCH_THRESHOLD = 85

ENTITY_SUFFIXES = {
    "llc",
    "l l c",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "lp",
    "l p",
    "lllp",
    "ltd",
    "limited",
    "trust",
    "trustees",
    "trustee",
    "et al",
    "et ux",
    "et vir",
}


@dataclass(frozen=True)
class ChainBreak:
    from_doc_index: int
    to_doc_index: int
    grantee_at_from: str
    grantor_at_to: str
    reason: str


def _normalize_party(name: str) -> str:
    name = name.lower()
    name = _NORMALIZE_RE.sub(" ", name)
    name = _WHITESPACE_RE.sub(" ", name).strip()
    tokens = [t for t in name.split() if t not in ENTITY_SUFFIXES]
    return " ".join(tokens)


def _names_match(a: str, b: str) -> bool:
    norm_a, norm_b = _normalize_party(a), _normalize_party(b)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    return fuzz.token_set_ratio(norm_a, norm_b) >= NAME_MATCH_THRESHOLD


def check_party_chain_consistency(
    chain: list[tuple[str, str]],
) -> list[ChainBreak]:
    """Walk a chain of (grantor, grantee) pairs in chronological order.

    Returns an empty list when the chain is sound; otherwise one ChainBreak
    per missing link.
    """

    breaks: list[ChainBreak] = []
    for i in range(len(chain) - 1):
        _, grantee = chain[i]
        next_grantor, _ = chain[i + 1]
        if not _names_match(grantee, next_grantor):
            breaks.append(
                ChainBreak(
                    from_doc_index=i,
                    to_doc_index=i + 1,
                    grantee_at_from=grantee,
                    grantor_at_to=next_grantor,
                    reason="grantee→grantor name mismatch",
                )
            )
    return breaks
