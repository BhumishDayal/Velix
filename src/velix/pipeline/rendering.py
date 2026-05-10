"""Shared helpers for rendering PDF pages into images for OCR/VLM tiers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image


def render_page_to_pil(
    pdf_path: Path, page_number: int, dpi: int = 200
) -> Image.Image:
    doc = pymupdf.open(pdf_path)
    try:
        page = doc.load_page(page_number)
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
    finally:
        doc.close()


def render_page_to_array(
    pdf_path: Path, page_number: int, dpi: int = 200
) -> np.ndarray:
    return np.array(render_page_to_pil(pdf_path, page_number, dpi=dpi))
