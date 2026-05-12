from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from PIL import Image

from .embedder import Embedder
from .index import IndexedPage, VelixIndex
from .page_rendering import render_pdf_pages

DEFAULT_BATCH_SIZE = 4


def _iter_manifest(manifest_path: Path) -> Iterator[dict[str, str]]:
    with open(manifest_path, encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def _resolve_pdf_path(raw: str, manifest_path: Path) -> Path | None:
    raw_path = Path(raw)
    if raw_path.is_absolute():
        candidates = [raw_path]
    else:
        candidates = [
            (manifest_path.parent / raw_path).resolve(),
            (Path.cwd() / raw_path).resolve(),
            raw_path.resolve(),
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def index_corpus(
    *,
    manifest_paths: list[Path],
    embedder: Embedder,
    index: VelixIndex,
    batch_size: int = DEFAULT_BATCH_SIZE,
    on_doc: callable | None = None,
) -> dict[str, int]:
    pending_pages: list[IndexedPage] = []
    pending_images: list[Image.Image] = []
    stats = {"docs": 0, "pages": 0, "skipped_missing_pdf": 0}

    def flush() -> None:
        if not pending_pages:
            return
        embeddings = embedder.embed_pages(pending_images)
        index.upsert_pages(pending_pages, embeddings)
        stats["pages"] += len(pending_pages)
        pending_pages.clear()
        pending_images.clear()

    for manifest_path in manifest_paths:
        for row in _iter_manifest(manifest_path):
            pdf_path = _resolve_pdf_path(row["file_path"], manifest_path)
            if pdf_path is None:
                stats["skipped_missing_pdf"] += 1
                continue

            try:
                metadata = json.loads(row.get("metadata_json", "{}") or "{}")
            except json.JSONDecodeError:
                metadata = {}

            stats["docs"] += 1
            for page_number, image in render_pdf_pages(pdf_path):
                pending_pages.append(
                    IndexedPage(
                        source=row["source"],
                        source_id=row["source_id"],
                        file_path=str(pdf_path),
                        page_number=page_number,
                        title=row.get("title", ""),
                        sha256=row.get("sha256", ""),
                        source_metadata=metadata,
                    )
                )
                pending_images.append(image)
                if len(pending_pages) >= batch_size:
                    flush()
            if on_doc is not None:
                on_doc(row, stats)

    flush()
    return stats
