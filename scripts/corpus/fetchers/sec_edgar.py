"""SEC EDGAR oil & gas fetcher.

Strategy:
1. Hit the EDGAR full-text search endpoint to discover filings matching
   oil/gas/lease keywords from companies in SIC 1311 (Crude Petroleum &
   Natural Gas Extraction).
2. For each matching filing, fetch its document index JSON to enumerate
   attached exhibits.
3. Yield FetchTasks for any PDF exhibit (skip HTML/XBRL — we want documents
   that round-trip to the visual pipeline).

SEC requires an identifying User-Agent for programmatic access; the base
fetcher sets one. Rate limit is 10 req/sec maximum per SEC's posted policy;
the base 1 req/sec floor is well inside that.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.parse import urlencode

from .base import FetchTask, Fetcher

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data"

OIL_GAS_SIC = "1311"
DEFAULT_QUERIES = [
    '"oil and gas lease"',
    '"mineral lease"',
    '"assignment of lease"',
    '"division order"',
    '"working interest"',
    '"royalty interest"',
    '"net mineral acres"',
    '"joint operating agreement"',
    '"oil and gas properties"',
    '"leasehold interest"',
    '"gross acreage"',
    '"undeveloped acreage"',
]
DEFAULT_FORMS = ["10-K", "S-1", "8-K", "S-11", "10-Q", "DEF 14A"]
EDGAR_PAGE_SIZE = 100  # max EDGAR full-text search will return per request


class SecEdgarFetcher(Fetcher):
    source_name = "sec_edgar"

    def __init__(
        self,
        *,
        queries: list[str] | None = None,
        forms: list[str] | None = None,
        sic: str | None = OIL_GAS_SIC,
        per_query_cap: int = 1000,
        **base_kwargs: object,
    ) -> None:
        super().__init__(**base_kwargs)
        self.queries = queries or DEFAULT_QUERIES
        self.forms = forms or DEFAULT_FORMS
        self.sic = sic
        self.per_query_cap = per_query_cap

    def _search_page(self, query: str, offset: int) -> tuple[list[dict], int]:
        """Return (hits_on_this_page, total_hits_reported)."""
        params = {
            "q": query,
            "forms": ",".join(self.forms),
            "category": "form-type",
            "from": offset,
            "size": EDGAR_PAGE_SIZE,
        }
        url = f"{EDGAR_SEARCH_URL}?{urlencode(params)}"
        response = self.request("GET", url)
        payload = response.json()
        outer = payload.get("hits", {})
        total = outer.get("total", {})
        if isinstance(total, dict):
            total_value = int(total.get("value", 0))
        else:
            total_value = int(total or 0)
        return outer.get("hits", []), total_value

    def _search(self, query: str) -> Iterator[dict]:
        """Yield filtered hits across all pages (up to per_query_cap)."""
        offset = 0
        emitted = 0
        while emitted < self.per_query_cap:
            page, total = self._search_page(query, offset)
            if not page:
                return
            for hit in page:
                if self.sic:
                    sics = hit.get("_source", {}).get("sics", []) or []
                    if self.sic not in sics:
                        continue
                yield hit
                emitted += 1
                if emitted >= self.per_query_cap:
                    return
            offset += EDGAR_PAGE_SIZE
            if offset >= total:
                return

    def _filing_index_url(self, cik: str, accession_no: str) -> str:
        accession_clean = accession_no.replace("-", "")
        return f"{EDGAR_ARCHIVE_URL}/{int(cik)}/{accession_clean}/index.json"

    def _archive_doc_url(self, cik: str, accession_no: str, filename: str) -> str:
        accession_clean = accession_no.replace("-", "")
        return f"{EDGAR_ARCHIVE_URL}/{int(cik)}/{accession_clean}/{filename}"

    def _enumerate_pdfs(self, cik: str, accession_no: str) -> Iterator[tuple[str, str]]:
        """Yield (filename, full_url) for every PDF in the filing."""
        try:
            response = self.request("GET", self._filing_index_url(cik, accession_no))
            index = response.json()
        except Exception:
            return
        for item in index.get("directory", {}).get("item", []):
            name = item.get("name", "")
            if name.lower().endswith(".pdf"):
                yield name, self._archive_doc_url(cik, accession_no, name)

    def discover(self, max_docs: int) -> Iterator[FetchTask]:
        seen_accessions: set[str] = set()
        emitted = 0
        for query in self.queries:
            if emitted >= max_docs:
                return
            try:
                hits = list(self._search(query))
            except Exception:
                continue
            for hit in hits:
                if emitted >= max_docs:
                    return
                source = hit.get("_source", {})
                # _id format: "0000950170-25-012345:document.htm"; we want the accession
                hit_id = hit.get("_id", "")
                accession_no = hit_id.split(":", 1)[0] if ":" in hit_id else hit_id
                if not accession_no or accession_no in seen_accessions:
                    continue
                seen_accessions.add(accession_no)
                ciks = source.get("ciks", [])
                if not ciks:
                    continue
                cik = ciks[0]
                form = source.get("form", "")
                display_names = source.get("display_names", []) or []
                company = display_names[0] if display_names else ""
                for filename, url in self._enumerate_pdfs(cik, accession_no):
                    if emitted >= max_docs:
                        return
                    yield FetchTask(
                        source_id=f"{accession_no}/{filename}",
                        url=url,
                        relative_path=f"sec_edgar/{accession_no}/{filename}",
                        content_type="application/pdf",
                        title=f"{company} {form} — {filename}",
                        metadata={
                            "cik": cik,
                            "accession_no": accession_no,
                            "form": form,
                            "company": company,
                            "query": query,
                        },
                    )
                    emitted += 1
