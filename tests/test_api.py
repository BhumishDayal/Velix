"""End-to-end tests for the FastAPI service via TestClient.

The mock embedder + mock extractor mean every endpoint is fully exercised
on CPU, including the indexing-then-querying-then-extracting roundtrip.
SQLite cache lives in tmp_path so tests are hermetic.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from velix.api.app import create_app
from velix.api.deps import AppConfig
from velix.api.document_store import DocumentRecord
from velix.retrieval import IndexedPage, MockEmbedder


def _fake_pdf(path: Path, *, pages: int) -> None:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i}")
    doc.save(path)
    doc.close()


def _write_manifest(manifest_path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "source",
        "source_id",
        "file_path",
        "page_count",
        "sha256",
        "content_type",
        "downloaded_at",
        "title",
        "metadata_json",
    ]
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Build a tiny corpus on disk and return the manifest path."""
    pdf_a = tmp_path / "a.pdf"
    pdf_b = tmp_path / "b.pdf"
    _fake_pdf(pdf_a, pages=2)
    _fake_pdf(pdf_b, pages=3)

    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            {
                "source": "tx_glo",
                "source_id": "1",
                "file_path": str(pdf_a),
                "page_count": "2",
                "sha256": "abc",
                "content_type": "application/pdf",
                "downloaded_at": "2026-05-10T00:00:00Z",
                "title": "Grant 1",
                "metadata_json": "{\"county\": \"Dallas\"}",
            },
            {
                "source": "sec_edgar",
                "source_id": "2",
                "file_path": str(pdf_b),
                "page_count": "3",
                "sha256": "def",
                "content_type": "application/pdf",
                "downloaded_at": "2026-05-10T00:00:00Z",
                "title": "Filing 2",
                "metadata_json": "{}",
            },
        ],
    )
    return manifest


@pytest.fixture
def client(corpus: Path, tmp_path: Path) -> TestClient:
    """A TestClient with a freshly-seeded index. We pre-populate the index
    inside the app's startup hook so /search has something to return."""
    config = AppConfig(
        manifest_paths=[corpus],
        qdrant_target="memory",
        cache_db_path=tmp_path / "cache.sqlite",
        use_mock_embedder=True,
        use_mock_extractor=True,
        require_pdf=True,
    )
    api = create_app(config)

    # Pre-seed the index with one page from the document store. The startup
    # hook builds the index but doesn't index any documents — we do that
    # explicitly here so /search has data.
    test_client = TestClient(api)
    with test_client:
        embedder: MockEmbedder = api.state.embedder
        from PIL import Image

        for record in api.state.documents.all(limit=10):
            for page_number in range(record.page_count):
                page = IndexedPage(
                    source=record.source,
                    source_id=record.source_id,
                    file_path=str(record.file_path),
                    page_number=page_number,
                    title=record.title,
                    sha256=record.sha256,
                    source_metadata=record.metadata,
                )
                embedding = embedder.embed_pages(
                    [Image.new("RGB", (100, 100), color=(page_number, 0, 0))]
                )[0]
                api.state.index.upsert_pages([page], [embedding])
        yield test_client


# ─────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["documents"] == 2
    assert body["indexed_pages"] == 5  # 2 + 3
    assert body["cached_extractions"] == 0


# ─────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────


def test_list_documents(client: TestClient) -> None:
    r = client.get("/documents")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["documents"]) == 2
    sources = {d["source"] for d in body["documents"]}
    assert sources == {"tx_glo", "sec_edgar"}


def test_list_documents_source_filter(client: TestClient) -> None:
    r = client.get("/documents?source=tx_glo")
    assert r.status_code == 200
    body = r.json()
    assert body["source_filter"] == "tx_glo"
    assert all(d["source"] == "tx_glo" for d in body["documents"])


def test_get_document(client: TestClient) -> None:
    r = client.get("/documents/tx_glo/1")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "tx_glo"
    assert body["source_id"] == "1"
    assert body["page_count"] == 2
    assert body["metadata"] == {"county": "Dallas"}


def test_get_document_404(client: TestClient) -> None:
    r = client.get("/documents/tx_glo/does_not_exist")
    assert r.status_code == 404


def test_get_document_pdf(client: TestClient) -> None:
    r = client.get("/documents/tx_glo/1/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    # Real PDF content (PDFs start with %PDF-)
    assert r.content[:4] == b"%PDF"


# ─────────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────────


def test_search_returns_ranked_hits(client: TestClient) -> None:
    r = client.get("/search?q=Dallas mineral grant&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "Dallas mineral grant"
    assert body["limit"] == 10
    assert len(body["hits"]) > 0
    # Hits sorted by score descending (Qdrant default)
    scores = [h["score"] for h in body["hits"]]
    assert scores == sorted(scores, reverse=True)


def test_search_source_filter(client: TestClient) -> None:
    r = client.get("/search?q=anything&source=sec_edgar")
    assert r.status_code == 200
    body = r.json()
    assert all(h["source"] == "sec_edgar" for h in body["hits"])


def test_search_requires_query(client: TestClient) -> None:
    r = client.get("/search?q=")
    assert r.status_code == 422  # min_length=1


# ─────────────────────────────────────────────────────────────────────────
# Extract
# ─────────────────────────────────────────────────────────────────────────


def test_extract_mineral_deed(client: TestClient) -> None:
    r = client.post(
        "/extract",
        json={
            "source": "tx_glo",
            "source_id": "1",
            "page_number": 0,
            "schema_name": "mineral_deed",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cached"] is False
    assert body["schema_name"] == "mineral_deed"
    assert body["extraction"]["document_type"] == "mineral_deed"
    assert body["extraction"]["grantor"]["full_name"]
    assert body["extraction"]["grantee"]["full_name"]


def test_extract_is_cached(client: TestClient) -> None:
    payload = {
        "source": "tx_glo",
        "source_id": "1",
        "page_number": 0,
        "schema_name": "mineral_deed",
    }
    r1 = client.post("/extract", json=payload)
    assert r1.status_code == 200
    assert r1.json()["cached"] is False

    r2 = client.post("/extract", json=payload)
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    # Same extraction returned
    assert r1.json()["extraction"] == r2.json()["extraction"]


def test_extract_refresh_bypasses_cache(client: TestClient) -> None:
    payload = {
        "source": "tx_glo",
        "source_id": "1",
        "page_number": 0,
        "schema_name": "mineral_deed",
    }
    client.post("/extract", json=payload)
    r = client.post("/extract?refresh=true", json=payload)
    assert r.status_code == 200
    assert r.json()["cached"] is False


def test_extract_unknown_schema(client: TestClient) -> None:
    r = client.post(
        "/extract",
        json={
            "source": "tx_glo",
            "source_id": "1",
            "page_number": 0,
            "schema_name": "not_a_real_schema",
        },
    )
    assert r.status_code == 400


def test_extract_unknown_document(client: TestClient) -> None:
    r = client.post(
        "/extract",
        json={
            "source": "tx_glo",
            "source_id": "999",
            "page_number": 0,
            "schema_name": "mineral_deed",
        },
    )
    assert r.status_code == 404


def test_extract_page_out_of_range(client: TestClient) -> None:
    r = client.post(
        "/extract",
        json={
            "source": "tx_glo",
            "source_id": "1",
            "page_number": 99,  # only 2 pages
            "schema_name": "mineral_deed",
        },
    )
    assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────
# Misc
# ─────────────────────────────────────────────────────────────────────────


def test_cors_header_present(client: TestClient) -> None:
    r = client.get("/health", headers={"origin": "https://example.com"})
    assert r.status_code == 200
    assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}
