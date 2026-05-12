from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from pydantic import BaseModel, Field

MANIFEST_FILENAME = "manifest.csv"


class ManifestEntry(BaseModel):
    source: str
    source_id: str
    file_path: str
    page_count: int
    sha256: str
    content_type: str
    downloaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str = ""
    metadata_json: str = "{}"


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _page_count_of_pdf(path: Path) -> int:
    try:
        with pymupdf.open(path) as doc:
            return doc.page_count
    except Exception:
        return 0


def make_entry(
    *,
    source: str,
    source_id: str,
    file_path: Path,
    content_type: str,
    title: str = "",
    metadata_json: str = "{}",
) -> ManifestEntry:
    page_count = _page_count_of_pdf(file_path) if content_type == "application/pdf" else 0
    return ManifestEntry(
        source=source,
        source_id=source_id,
        file_path=str(file_path),
        page_count=page_count,
        sha256=_sha256_of_file(file_path),
        content_type=content_type,
        title=title,
        metadata_json=metadata_json,
    )


class Manifest:
    def __init__(self, corpus_root: Path) -> None:
        self.corpus_root = corpus_root
        self.path = corpus_root / MANIFEST_FILENAME
        self._seen_ids: set[tuple[str, str]] = set()
        self._load_existing()

    def _load_existing(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self._seen_ids.add((row["source"], row["source_id"]))

    def has(self, source: str, source_id: str) -> bool:
        return (source, source_id) in self._seen_ids

    def append(self, entry: ManifestEntry) -> None:
        write_header = not self.path.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(ManifestEntry.model_fields.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(entry.model_dump(mode="json"))
        self._seen_ids.add((entry.source, entry.source_id))

    def total_pages(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8", newline="") as f:
            return sum(int(row["page_count"] or 0) for row in csv.DictReader(f))

    def count_by_source(self) -> dict[str, int]:
        if not self.path.exists():
            return {}
        counts: dict[str, int] = {}
        with open(self.path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                counts[row["source"]] = counts.get(row["source"], 0) + 1
        return counts
