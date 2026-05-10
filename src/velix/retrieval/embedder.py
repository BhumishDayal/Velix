"""Embedder interface and implementations.

Two implementations:

- MockEmbedder: deterministic, hash-based, CPU-only. Lets the rest of the
  retrieval stack be tested without GPUs or model downloads.
- ColQwen2Embedder: the real ColPali-engine ColQwen2 embedder. Requires a
  GPU and the [retrieval] extras (colpali-engine, torch, transformers).
  Imported lazily so this module loads on CPU-only environments.

Both produce **multi-vector embeddings**: a 2-D array of shape
(num_tokens_or_patches, embedding_dim). Pages have many patches; queries
have many text tokens. Late interaction (MaxSim) at search time scores the
match between every query token and the most similar page patch, then
sums the per-token maxima. Qdrant 1.10+ executes this natively.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import numpy as np
from PIL import Image


class Embedder(ABC):
    """Common interface for any visual late-interaction embedder."""

    embedding_dim: int

    @abstractmethod
    def embed_pages(self, images: list[Image.Image]) -> list[np.ndarray]:
        """Embed a batch of page images.

        Returns one (num_patches, embedding_dim) float32 array per image.
        """

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query string.

        Returns a (num_query_tokens, embedding_dim) float32 array.
        """


def _seed_to_unit_vector(seed_bytes: bytes, dim: int) -> np.ndarray:
    """Map an arbitrary byte string to a deterministic unit vector."""
    out = np.zeros(dim, dtype=np.float32)
    digest = hashlib.sha256(seed_bytes).digest()
    # Repeat-extend the digest into `dim` floats deterministically.
    needed = dim * 4  # float32 = 4 bytes
    extended = (digest * ((needed // len(digest)) + 1))[:needed]
    out[:] = np.frombuffer(extended, dtype=np.uint32).astype(np.float32)
    out -= out.mean()
    norm = np.linalg.norm(out)
    if norm > 0:
        out /= norm
    return out


class MockEmbedder(Embedder):
    """Hashes inputs to deterministic unit vectors of the same shape ColQwen2
    would produce. Identical inputs always produce identical embeddings, so
    tests can assert exact ranking behaviour."""

    def __init__(
        self,
        *,
        embedding_dim: int = 128,
        patches_per_page: int = 32,
        tokens_per_query: int = 8,
    ) -> None:
        self.embedding_dim = embedding_dim
        self.patches_per_page = patches_per_page
        self.tokens_per_query = tokens_per_query

    def embed_pages(self, images: list[Image.Image]) -> list[np.ndarray]:
        results: list[np.ndarray] = []
        for image in images:
            seed = image.tobytes()
            vectors = np.zeros(
                (self.patches_per_page, self.embedding_dim), dtype=np.float32
            )
            for i in range(self.patches_per_page):
                vectors[i] = _seed_to_unit_vector(
                    seed + i.to_bytes(4, "little"), self.embedding_dim
                )
            results.append(vectors)
        return results

    def embed_query(self, text: str) -> np.ndarray:
        seed = text.encode("utf-8")
        vectors = np.zeros(
            (self.tokens_per_query, self.embedding_dim), dtype=np.float32
        )
        for i in range(self.tokens_per_query):
            vectors[i] = _seed_to_unit_vector(
                seed + b"q" + i.to_bytes(4, "little"), self.embedding_dim
            )
        return vectors


class ColQwen2Embedder(Embedder):
    """Real ColQwen2 embedder. GPU required. Heavy imports are deferred so
    importing the retrieval package is cheap on CPU-only machines."""

    def __init__(
        self,
        *,
        model_name: str = "vidore/colqwen2-v1.0",
        device: str = "cuda",
        dtype: str = "bfloat16",
    ) -> None:
        import torch  # local import: heavy
        from colpali_engine.models import ColQwen2, ColQwen2Processor  # local import

        torch_dtype = getattr(torch, dtype)
        self._torch = torch
        self._device = device
        self.model = ColQwen2.from_pretrained(
            model_name, torch_dtype=torch_dtype, device_map=device
        ).eval()
        self.processor = ColQwen2Processor.from_pretrained(model_name)
        self.embedding_dim = int(self.model.config.hidden_size)

    def embed_pages(self, images: list[Image.Image]) -> list[np.ndarray]:
        torch = self._torch
        with torch.no_grad():
            batch = self.processor.process_images(images).to(self._device)
            embeddings = self.model(**batch)
        return [page.cpu().to(torch.float32).numpy() for page in embeddings]

    def embed_query(self, text: str) -> np.ndarray:
        torch = self._torch
        with torch.no_grad():
            batch = self.processor.process_queries([text]).to(self._device)
            embeddings = self.model(**batch)
        return embeddings[0].cpu().to(torch.float32).numpy()
