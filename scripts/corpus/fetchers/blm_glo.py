"""BLM General Land Office Records fetcher — DEFERRED IMPLEMENTATION.

The BLM GLO Records site at https://glorecords.blm.gov/ does not expose
patent images via static URLs. The "Patent Image" tab on each details page
is loaded by client-side JavaScript that posts to an internal handler;
neither the search results nor the details page contain a direct PDF URL
in their static HTML.

To implement this fetcher we have two viable paths:

1. **Reverse-engineer the JS endpoint.** Open the Patent Details page in a
   browser DevTools Network panel, click "Patent Image", and capture the
   request the JS makes. It is likely a POST to
   `/PatentSearch/PatentImageHandler.aspx` or similar with the accession +
   docClass as form fields, returning a PDF or TIFF stream.

2. **Browser automation with Playwright.** Spin up a headless Chromium
   session, drive the search → details → image-tab clicks, and intercept
   the resulting download. Heavier, but resilient to site redesigns.

Either way, candidate accession ranges to target (oil-rich federal-land
states; Texas is excluded because it is a state-land state):
  - Oklahoma (docClass = SER, OK)
  - New Mexico (NMLSR, NMLSRA)
  - Wyoming (WYAZAA, etc.)

Until this fetcher is implemented, the Velix demo corpus is built from
SEC EDGAR (modern oil & gas filings) and Texas GLO (historical scanned
grants). That mix is sufficient to demonstrate the value proposition;
BLM-GLO would broaden geographic coverage but is not on the critical
path to the interview demo.
"""

from __future__ import annotations

from collections.abc import Iterator

from .base import FetchTask, Fetcher


class BlmGloFetcher(Fetcher):  # pragma: no cover - intentionally unimplemented
    source_name = "blm_glo"

    def discover(self, max_docs: int) -> Iterator[FetchTask]:
        raise NotImplementedError(
            "BLM-GLO fetcher is deferred. See module docstring for the two "
            "viable implementation paths and why this is non-blocking for the "
            "demo corpus."
        )
