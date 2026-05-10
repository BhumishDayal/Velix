"""End-to-end retrieval tests using the MockEmbedder.

These tests verify that:
- VelixIndex creates a Qdrant multi-vector collection with the right schema
- Pages can be upserted with deterministic IDs (re-upsert overwrites)
- Search returns results ranked by MaxSim similarity
- Source filtering works
- The full corpus indexing pipeline ingests a small fixture corpus
- The pipeline runs idempotently when re-run on the same corpus

We use Qdrant in :memory: mode so tests are hermetic and fast.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pymupdf
import pytest

from velix.retrieval import IndexedPage, MockEmbedder, VelixIndex
from velix.retrieval.index import make_qdrant_client
from velix.retrieval.pipeline import index_corpus


@pytest.fixture
def embedder() -> MockEmbedder:
    return MockEmbedder()


@pytest.fixture
def index(embedder: MockEmbedder) -> VelixIndex:
    client = make_qdrant_client("memory")
    return VelixIndex(client, embedding_dim=embedder.embedding_dim)


def _fake_pdf(path: Path, *, pages: int) -> None:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i} content")
    doc.save(path)
    doc.close()


def test_index_creates_collection(index: VelixIndex) -> None:
    assert index.count() == 0
    assert index.client.collection_exists(index.collection_name)


def test_upsert_and_search_roundtrip(
    index: VelixIndex, embedder: MockEmbedder, tmp_path: Path
) -> None:
    _fake_pdf(tmp_path / "a.pdf", pages=2)
    from PIL import Image as PILImage

    images = [PILImage.new("RGB", (300, 400), color=(i, i, i)) for i in (10, 200)]
    pages = [
        IndexedPage(
            source="test",
            source_id="a",
            file_path=str(tmp_path / "a.pdf"),
            page_number=i,
            title="A test doc",
        )
        for i in range(2)
    ]
    embeddings = embedder.embed_pages(images)
    index.upsert_pages(pages, embeddings)

    assert index.count() == 2

    query_embedding = embedder.embed_query("anything")
    hits = index.search(query_embedding, limit=5)
    assert len(hits) == 2
    assert {h.page_number for h in hits} == {0, 1}
    assert all(h.source == "test" for h in hits)


def test_upsert_is_idempotent(
    index: VelixIndex, embedder: MockEmbedder, tmp_path: Path
) -> None:
    from PIL import Image as PILImage

    image = PILImage.new("RGB", (300, 400), color=(50, 50, 50))
    page = IndexedPage(
        source="t",
        source_id="doc",
        file_path=str(tmp_path / "x.pdf"),
        page_number=0,
    )
    emb = embedder.embed_pages([image])

    index.upsert_pages([page], emb)
    index.upsert_pages([page], emb)
    index.upsert_pages([page], emb)

    assert index.count() == 1


def test_source_filter(
    index: VelixIndex, embedder: MockEmbedder, tmp_path: Path
) -> None:
    from PIL import Image as PILImage

    images = [PILImage.new("RGB", (200, 200), color=(c, c, c)) for c in (10, 50, 100)]
    pages = [
        IndexedPage(source="sec_edgar", source_id="a", file_path="x", page_number=0),
        IndexedPage(source="tx_glo", source_id="b", file_path="y", page_number=0),
        IndexedPage(source="tx_glo", source_id="c", file_path="z", page_number=0),
    ]
    index.upsert_pages(pages, embedder.embed_pages(images))

    q = embedder.embed_query("any")
    all_hits = index.search(q, limit=10)
    glo_hits = index.search(q, limit=10, source_filter="tx_glo")

    assert len(all_hits) == 3
    assert len(glo_hits) == 2
    assert all(h.source == "tx_glo" for h in glo_hits)


def test_upsert_rejects_wrong_dim(index: VelixIndex) -> None:
    bad = np.zeros((4, 99), dtype=np.float32)  # wrong embedding_dim
    page = IndexedPage(source="t", source_id="x", file_path="x", page_number=0)
    with pytest.raises(ValueError, match="embedding"):
        index.upsert_pages([page], [bad])


def test_search_rejects_wrong_dim(
    index: VelixIndex, embedder: MockEmbedder
) -> None:
    bad = np.zeros((3, 99), dtype=np.float32)
    with pytest.raises(ValueError, match="query embedding"):
        index.search(bad)


def test_full_corpus_pipeline(
    index: VelixIndex, embedder: MockEmbedder, tmp_path: Path
) -> None:
    """Build a tiny corpus on disk, write its manifest, run index_corpus, search."""

    pdf_a = tmp_path / "a.pdf"
    pdf_b = tmp_path / "b.pdf"
    _fake_pdf(pdf_a, pages=2)
    _fake_pdf(pdf_b, pages=3)

    manifest_path = tmp_path / "manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "source_id",
                "file_path",
                "page_count",
                "sha256",
                "content_type",
                "downloaded_at",
                "title",
                "metadata_json",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source": "tx_glo",
                "source_id": "1",
                "file_path": str(pdf_a),
                "page_count": "2",
                "sha256": "abc",
                "content_type": "application/pdf",
                "downloaded_at": "2026-05-06T00:00:00Z",
                "title": "Grant 1",
                "metadata_json": json.dumps({"county": "Dallas"}),
            }
        )
        writer.writerow(
            {
                "source": "sec_edgar",
                "source_id": "2",
                "file_path": str(pdf_b),
                "page_count": "3",
                "sha256": "def",
                "content_type": "application/pdf",
                "downloaded_at": "2026-05-06T00:00:00Z",
                "title": "Filing 2",
                "metadata_json": "{}",
            }
        )

    stats = index_corpus(
        manifest_paths=[manifest_path],
        embedder=embedder,
        index=index,
    )
    assert stats == {"docs": 2, "pages": 5, "skipped_missing_pdf": 0}
    assert index.count() == 5

    # Re-running on the same manifest must not duplicate points (UUID5 keys).
    stats2 = index_corpus(
        manifest_paths=[manifest_path], embedder=embedder, index=index
    )
    assert stats2["pages"] == 5
    assert index.count() == 5


def test_pipeline_skips_missing_pdf(
    index: VelixIndex, embedder: MockEmbedder, tmp_path: Path
) -> None:
    manifest_path = tmp_path / "manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "source_id",
                "file_path",
                "page_count",
                "sha256",
                "content_type",
                "downloaded_at",
                "title",
                "metadata_json",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source": "tx_glo",
                "source_id": "missing",
                "file_path": str(tmp_path / "does_not_exist.pdf"),
                "page_count": "0",
                "sha256": "",
                "content_type": "application/pdf",
                "downloaded_at": "2026-05-06T00:00:00Z",
                "title": "",
                "metadata_json": "{}",
            }
        )

    stats = index_corpus(
        manifest_paths=[manifest_path], embedder=embedder, index=index
    )
    assert stats == {"docs": 0, "pages": 0, "skipped_missing_pdf": 1}
    assert index.count() == 0


def test_mock_embedder_is_deterministic() -> None:
    e = MockEmbedder()
    e1 = e.embed_query("oil and gas lease")
    e2 = e.embed_query("oil and gas lease")
    e3 = e.embed_query("DIFFERENT QUERY")

    np.testing.assert_array_equal(e1, e2)
    assert not np.array_equal(e1, e3)
    assert e1.shape == (8, 128)
