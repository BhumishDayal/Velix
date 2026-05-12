from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SOURCE_ID_SLASH_REPLACEMENT = "--"


def _url_safe_source_id(raw: str) -> str:
    """``/`` in source_ids breaks single-segment route matching after URL
    decoding. Swap to a non-conflicting separator. Idempotent."""
    return raw.replace("/", SOURCE_ID_SLASH_REPLACEMENT)


@dataclass(frozen=True)
class DocumentRecord:
    source: str
    source_id: str
    source_id_raw: str
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
