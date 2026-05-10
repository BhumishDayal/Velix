import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    tier2_olmocr_device: str = os.getenv("TIER2_OLMOCR_DEVICE", "cuda")
    tier2_olmocr_model: str = os.getenv("TIER2_OLMOCR_MODEL", "allenai/olmOCR-7B-0825")
    tier1_confidence_threshold: float = float(os.getenv("TIER1_CONFIDENCE_THRESHOLD", "0.85"))
    tier2_confidence_threshold: float = float(os.getenv("TIER2_CONFIDENCE_THRESHOLD", "0.92"))
    tier3_confidence_threshold: float = float(os.getenv("TIER3_CONFIDENCE_THRESHOLD", "0.80"))
    tier3_enabled: bool = os.getenv("TIER3_ENABLED", "false").lower() == "true"


settings = Settings()
