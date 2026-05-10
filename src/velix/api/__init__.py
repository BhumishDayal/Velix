"""FastAPI service exposing search, extraction, and document browse over the
indexed corpus. Same mock-or-real pattern as the rest of the project: the
service runs end-to-end on CPU with the mock embedder/extractor for tests
and local dev; production swaps in ColQwen2 + Qwen2.5-VL on a GPU pod.
"""

from .app import create_app

__all__ = ["create_app"]
