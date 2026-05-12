from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import numpy as np
from PIL import Image


class Embedder(ABC):
    embedding_dim: int

    @abstractmethod
    def embed_pages(self, images: list[Image.Image]) -> list[np.ndarray]: ...

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray: ...


def _seed_to_unit_vector(seed_bytes: bytes, dim: int) -> np.ndarray:
    out = np.zeros(dim, dtype=np.float32)
    digest = hashlib.sha256(seed_bytes).digest()
    needed = dim * 4
    extended = (digest * ((needed // len(digest)) + 1))[:needed]
    out[:] = np.frombuffer(extended, dtype=np.uint32).astype(np.float32)
    out -= out.mean()
    norm = np.linalg.norm(out)
    if norm > 0:
        out /= norm
    return out


class MockEmbedder(Embedder):
    """Deterministic hash-based embedder for CPU tests. Same shape as
    ColQwen2 but the rankings aren't semantic."""

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
    """ColQwen2-v1.0 visual embedder. Requires GPU + the [retrieval] extras."""

    def __init__(
        self,
        *,
        model_name: str = "vidore/colqwen2-v1.0",
        device: str = "cuda",
        dtype: str = "bfloat16",
    ) -> None:
        import torch

        # Latest transformers calls peft._maybe_shard_state_dict_for_tp during
        # adapter loading; the function only exists in peft main. No-op shim
        # since we don't use tensor parallelism.
        import peft.utils.save_and_load as _ps
        if not hasattr(_ps, "_maybe_shard_state_dict_for_tp"):
            _ps._maybe_shard_state_dict_for_tp = (
                lambda state_dict, *args, **kwargs: state_dict
            )

        from colpali_engine.models import ColQwen2, ColQwen2Processor

        torch_dtype = getattr(torch, dtype)
        self._torch = torch
        self._device = device
        self.model = ColQwen2.from_pretrained(
            model_name, torch_dtype=torch_dtype, device_map=device
        ).eval()
        self.processor = ColQwen2Processor.from_pretrained(model_name)

        # ColPali variants project to a fixed dim regardless of base LLM.
        if hasattr(self.model, "dim"):
            self.embedding_dim = int(self.model.dim)
        elif hasattr(self.model, "custom_text_proj"):
            self.embedding_dim = int(self.model.custom_text_proj.out_features)
        else:
            self.embedding_dim = 128

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
