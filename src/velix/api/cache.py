from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS extractions (
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    page_number   INTEGER NOT NULL,
    schema_name   TEXT NOT NULL,
    payload_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (source, source_id, page_number, schema_name)
);
"""


class ExtractionCache:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(_SCHEMA)
            await conn.commit()

    @asynccontextmanager
    async def _conn(self):
        async with aiosqlite.connect(self.db_path) as conn:
            yield conn

    async def get(
        self, source: str, source_id: str, page_number: int, schema_name: str
    ) -> dict[str, Any] | None:
        async with self._conn() as conn:
            async with conn.execute(
                "SELECT payload_json FROM extractions WHERE "
                "source = ? AND source_id = ? AND page_number = ? AND schema_name = ?",
                (source, source_id, page_number, schema_name),
            ) as cur:
                row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def set(
        self,
        source: str,
        source_id: str,
        page_number: int,
        schema_name: str,
        payload: dict[str, Any],
    ) -> None:
        async with self._conn() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO extractions "
                "(source, source_id, page_number, schema_name, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    source,
                    source_id,
                    page_number,
                    schema_name,
                    json.dumps(payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await conn.commit()

    async def clear(self) -> None:
        async with self._conn() as conn:
            await conn.execute("DELETE FROM extractions")
            await conn.commit()

    async def count(self) -> int:
        async with self._conn() as conn:
            async with conn.execute("SELECT COUNT(*) FROM extractions") as cur:
                row = await cur.fetchone()
        return int(row[0]) if row else 0
