from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from velix.models import PageExtraction, Tier


class TierExtractor(ABC):
    """Common interface every tier implementation must satisfy.

    A tier returns a PageExtraction for one page; the orchestrator decides
    whether to accept it or escalate. Tiers must never raise on bad input;
    they must return a PageExtraction with confidence=0 and a note.
    """

    tier: Tier

    @abstractmethod
    def extract_page(self, pdf_path: Path, page_number: int) -> PageExtraction: ...

    def is_available(self) -> bool:
        """Whether the tier can run in the current environment."""

        return True
