"""Visual-first retrieval layer.

ColQwen2 multi-vector embeddings stored in Qdrant with MaxSim late
interaction. The MockEmbedder lets the entire pipeline (rendering,
indexing, querying, ranking, payload filtering) run on CPU for tests;
swap in ColQwen2Embedder when a GPU is available.
"""

from .embedder import Embedder, MockEmbedder
from .index import IndexedPage, SearchHit, VelixIndex
from .page_rendering import render_pdf_pages

__all__ = [
    "Embedder",
    "MockEmbedder",
    "VelixIndex",
    "IndexedPage",
    "SearchHit",
    "render_pdf_pages",
]
