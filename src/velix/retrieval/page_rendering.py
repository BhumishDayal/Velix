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
    with pymupdf.open(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for page_number in range(doc.page_count):
            page = doc.load_page(page_number)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            yield page_number, image
