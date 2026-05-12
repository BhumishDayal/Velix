from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel
from qdrant_client import QdrantClient, models

DEFAULT_COLLECTION = "velix_pages"


def make_qdrant_client(target: str | Path) -> QdrantClient:
    """``"memory"`` for tests, ``http(s)://...`` for remote, anything else
    treated as a file-backed local store."""
    target_str = str(target)
    if target_str in ("memory", ":memory:"):
        return QdrantClient(":memory:")
    if target_str.startswith(("http://", "https://")):
        return QdrantClient(url=target_str)
    return QdrantClient(path=target_str)


class IndexedPage(BaseModel):
    source: str
    source_id: str
    file_path: str
    page_number: int
    title: str = ""
    sha256: str = ""
    source_metadata: dict[str, Any] = {}


@dataclass
class SearchHit:
    score: float
    source: str
    source_id: str
    page_number: int
    file_path: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)


class VelixIndex:
    def __init__(
        self,
        client: QdrantClient,
        *,
        embedding_dim: int,
        collection_name: str = DEFAULT_COLLECTION,
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.embedding_dim,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM,
                ),
            ),
        )

    def upsert_pages(
        self,
        pages: list[IndexedPage],
        embeddings: list[np.ndarray],
    ) -> None:
        if len(pages) != len(embeddings):
            raise ValueError(
                f"pages ({len(pages)}) and embeddings ({len(embeddings)}) "
                "must have the same length"
            )
        points: list[models.PointStruct] = []
        for page, vectors in zip(pages, embeddings, strict=True):
            if vectors.ndim != 2 or vectors.shape[1] != self.embedding_dim:
                raise ValueError(
                    f"expected (N, {self.embedding_dim}) embedding for "
                    f"{page.source}/{page.source_id} p{page.page_number}, "
                    f"got shape {vectors.shape}"
                )
            point_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{page.source}|{page.source_id}|{page.page_number}",
            )
            points.append(
                models.PointStruct(
                    id=str(point_id),
                    vector=vectors.tolist(),
                    payload={
                        "source": page.source,
                        "source_id": page.source_id,
                        "file_path": page.file_path,
                        "page_number": page.page_number,
                        "title": page.title,
                        "sha256": page.sha256,
                        "source_metadata": page.source_metadata,
                    },
                )
            )
        self.client.upsert(self.collection_name, points=points)

    def search(
        self,
        query_embedding: np.ndarray,
        *,
        limit: int = 10,
        source_filter: str | None = None,
        source_id_filter: str | None = None,
    ) -> list[SearchHit]:
        if query_embedding.ndim != 2 or query_embedding.shape[1] != self.embedding_dim:
            raise ValueError(
                f"expected (N, {self.embedding_dim}) query embedding, "
                f"got shape {query_embedding.shape}"
            )
        conditions: list[models.FieldCondition] = []
        if source_filter is not None:
            conditions.append(
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=source_filter),
                )
            )
        if source_id_filter is not None:
            conditions.append(
                models.FieldCondition(
                    key="source_id",
                    match=models.MatchValue(value=source_id_filter),
                )
            )
        qdrant_filter = models.Filter(must=conditions) if conditions else None
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=limit,
            with_payload=True,
            query_filter=qdrant_filter,
        )
        hits: list[SearchHit] = []
        for point in response.points:
            payload = point.payload or {}
            hits.append(
                SearchHit(
                    score=float(point.score),
                    source=str(payload.get("source", "")),
                    source_id=str(payload.get("source_id", "")),
                    page_number=int(payload.get("page_number", -1)),
                    file_path=str(payload.get("file_path", "")),
                    title=str(payload.get("title", "")),
                    payload=payload,
                )
            )
        return hits

    def count(self) -> int:
        return int(self.client.count(self.collection_name, exact=True).count)
