"""PDF → page-image rendering for visual indexing.

We render at a moderate DPI (default 144) so embedders that crop / resize
to ~1024px get a clean page. Higher DPI buys nothing for visual retrieval
since ColQwen2's input resolution is bounded by the vision encoder.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pymupdf
from PIL import Image

DEFAULT_DPI = 144


def render_pdf_pages(
    pdf_path: Path | str,
    *,
    dpi: int = DEFAULT_DPI,
) -> Iterator[tuple[int, Image.Image]]:
    """Yield (page_number, PIL.Image) for each page in the PDF.

    page_number is 0-indexed. Caller is responsible for closing/dropping
    images once consumed (PIL Images are normal Python objects and free
    on garbage collection).
    """
    with pymupdf.open(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for page_number in range(doc.page_count):
            page = doc.load_page(page_number)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            yield page_number, image
