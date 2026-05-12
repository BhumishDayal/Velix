"""In-memory document index loaded from corpus manifest CSVs at startup.

Demo corpus is small (~200 docs); fits trivially in memory. Per row we keep
the metadata the search/extract endpoints need, plus the resolved absolute
PDF path so route handlers don't need to deal with manifest-relative paths.

Source IDs that contain ``/`` (e.g. SEC EDGAR's ``<accession>/<filename>``)
are normalized to use ``--`` instead, since FastAPI/uvicorn decodes ``%2F``
back to ``/`` before route matching, which would split the segment and
break the ``/documents/{source}/{source_id}`` route. The original value
stays accessible via ``DocumentRecord.source_id_raw``.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SOURCE_ID_SLASH_REPLACEMENT = "--"


def _url_safe_source_id(raw: str) -> str:
    """Make a source_id usable as a single URL path segment.

    SEC EDGAR ids contain ``/`` (``<accession>/<filename>``) which collides
    with FastAPI route matching after uvicorn URL-decodes ``%2F``. Swap to
    a non-conflicting separator. Idempotent; safe to call repeatedly.
    """
    return raw.replace("/", SOURCE_ID_SLASH_REPLACEMENT)


@dataclass(frozen=True)
class DocumentRecord:
    source: str
    source_id: str  # URL-safe form (no '/')
    source_id_raw: str  # original value from the manifest
    file_path: Path
    page_count: int
    sha256: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return (self.source, self.source_id)


def _resolve_pdf_path(raw: str, manifest_path: Path) -> Path | None:
    raw_path = Path(raw)
    candidates: list[Path]
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


class DocumentStore:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], DocumentRecord] = {}

    @classmethod
    def from_manifests(
        cls, manifest_paths: list[Path], *, require_pdf: bool = False
    ) -> DocumentStore:
        store = cls()
        for manifest_path in manifest_paths:
            if not manifest_path.exists():
                continue
            with open(manifest_path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    pdf_path = _resolve_pdf_path(row["file_path"], manifest_path)
                    if pdf_path is None:
                        if require_pdf:
                            continue
                        # Keep the metadata even if the PDF is missing (e.g.,
                        # in CI where corpus PDFs aren't bundled). file_path
                        # falls back to the unresolved manifest value.
                        pdf_path = Path(row["file_path"])
                    try:
                        metadata = json.loads(row.get("metadata_json", "{}") or "{}")
                    except json.JSONDecodeError:
                        metadata = {}
                    raw_source_id = row["source_id"]
                    record = DocumentRecord(
                        source=row["source"],
                        source_id=_url_safe_source_id(raw_source_id),
                        source_id_raw=raw_source_id,
                        file_path=pdf_path,
                        page_count=int(row.get("page_count") or 0),
                        sha256=row.get("sha256", ""),
                        title=row.get("title", ""),
                        metadata=metadata,
                    )
                    store._by_key[record.key] = record
        return store

    def add(self, record: DocumentRecord) -> None:
        self._by_key[record.key] = record

    def get(self, source: str, source_id: str) -> DocumentRecord | None:
        # Accept either URL-safe (--) or raw (/) form so legacy links work.
        return self._by_key.get((source, _url_safe_source_id(source_id)))

    def all(
        self,
        *,
        source: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[DocumentRecord]:
        records = list(self._by_key.values())
        if source is not None:
            records = [r for r in records if r.source == source]
        return records[offset : offset + limit]

    def __len__(self) -> int:
        return len(self._by_key)
