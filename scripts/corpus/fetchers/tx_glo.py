from __future__ import annotations

import re
from collections.abc import Iterator

import httpx
from bs4 import BeautifulSoup

from .base import FetchTask, Fetcher

GRANT_BASE_URL = (
    "https://www.glo.texas.gov/archives-heritage/search-our-collections"
    "/land-grant-search/land-grant"
)
_PDF_HREF_RE = re.compile(r"\.pdf(?:[?#]|$)", re.IGNORECASE)
_CDN_HOST_RE = re.compile(r"cdn\.glo\.texas\.gov", re.IGNORECASE)


class TexasGloFetcher(Fetcher):
    source_name = "tx_glo"

    def __init__(
        self,
        *,
        start_id: int = 1,
        end_id: int = 50_000,
        consecutive_miss_limit: int = 200,
        **base_kwargs: object,
    ) -> None:
        super().__init__(**base_kwargs)
        self.start_id = start_id
        self.end_id = end_id
        self.consecutive_miss_limit = consecutive_miss_limit

    def _parse_grant_page(self, html: str) -> tuple[dict, str | None]:
        soup = BeautifulSoup(html, "html.parser")

        pdf_url: str | None = None
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if _CDN_HOST_RE.search(href) and _PDF_HREF_RE.search(href):
                pdf_url = href
                break
        if pdf_url is None:
            for anchor in soup.find_all("a", href=True):
                text = anchor.get_text(strip=True).lower()
                if "view pdf" in text and _PDF_HREF_RE.search(anchor["href"]):
                    pdf_url = anchor["href"]
                    break

        metadata: dict[str, str] = {}

        # GLO uses a Foundation grid: <strong> label inside a div, value in
        # the next sibling div. Walk strong tags to pull both.
        for strong in soup.find_all("strong"):
            label_text = strong.get_text(strip=True).rstrip(":").strip()
            if not label_text:
                continue
            label_div = strong.find_parent("div")
            if label_div is None:
                continue
            value_div = label_div.find_next_sibling("div")
            if value_div is None:
                continue
            value_text = value_div.get_text(strip=True)
            if not value_text:
                continue
            key = label_text.lower().replace(" ", "_").replace("/", "_")
            metadata.setdefault(key, value_text)

        # Fallback: classic dt/dd or th/td if a future page is restyled.
        if not metadata:
            for label_tag, value_tag in (("dt", "dd"), ("th", "td")):
                for label in soup.find_all(label_tag):
                    value = label.find_next(value_tag)
                    if value is None:
                        continue
                    key = (
                        label.get_text(strip=True).rstrip(":").lower().replace(" ", "_")
                    )
                    if not key:
                        continue
                    metadata.setdefault(key, value.get_text(strip=True))

        return metadata, pdf_url

    def discover(self, max_docs: int) -> Iterator[FetchTask]:
        emitted = 0
        consecutive_misses = 0
        for grant_id in range(self.start_id, self.end_id):
            if emitted >= max_docs:
                return
            if consecutive_misses >= self.consecutive_miss_limit:
                return
            try:
                response = self.request("GET", f"{GRANT_BASE_URL}/{grant_id}")
            except httpx.HTTPError:
                consecutive_misses += 1
                continue

            metadata, pdf_url = self._parse_grant_page(response.text)
            if not pdf_url:
                consecutive_misses += 1
                continue

            consecutive_misses = 0
            grantee = (
                metadata.get("original_grantee")
                or metadata.get("grantee")
                or metadata.get("patentee")
                or ""
            )
            county = metadata.get("county", "")
            title_parts = [f"Texas Land Grant {grant_id}"]
            if grantee:
                title_parts.append(grantee)
            if county:
                title_parts.append(f"{county} County")
            title = " — ".join(title_parts)

            yield FetchTask(
                source_id=str(grant_id),
                url=pdf_url,
                relative_path=f"tx_glo/{grant_id}.pdf",
                content_type="application/pdf",
                title=title,
                metadata={"grant_id": grant_id, **metadata},
            )
            emitted += 1
