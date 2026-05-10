"""Modal deployment for the Velix FastAPI service.

Deploys the same FastAPI app from ``src/velix/api/`` as a serverless web
endpoint on Modal. Scales to zero when idle (free), spins up on first
request (~2-5s cold start).

This first deployment uses the MockEmbedder + MockExtractor — no GPU. Search
returns ranked results based on hashed embeddings (the plumbing works,
ranking isn't semantic). To activate the real ColQwen2 + Qwen2.5-VL models
later, see "GPU activation" at the bottom of this file.

──────────────────────────────────────────────────────────────────────────────
Deployment workflow (run these from the repo root, in any conda env)
──────────────────────────────────────────────────────────────────────────────

1. Install the Modal CLI:
       pip install modal

2. Authenticate (opens a browser; one-time):
       modal token new

3. Create the persistent volume that will hold the index + manifests:
       modal volume create velix-data

4. Build the local Qdrant index if you haven't already:
       conda activate velix
       python -m velix.cli index --manifest corpus_glo/manifest.csv `
           --manifest corpus_sec/manifest.csv --index velix_index --mock

5. Upload the index and manifests to the volume:
       modal volume put velix-data velix_index /velix_index
       modal volume put velix-data corpus_glo/manifest.csv /manifests/corpus_glo.csv
       modal volume put velix-data corpus_sec/manifest.csv /manifests/corpus_sec.csv

6. Deploy the app:
       modal deploy modal_app.py

   Modal prints a public URL on success — looks like
   https://bhumishdayal--velix-velix-api.modal.run

7. Verify:
       curl https://bhumishdayal--velix-velix-api.modal.run/health

──────────────────────────────────────────────────────────────────────────────
Caveats for this first deployment
──────────────────────────────────────────────────────────────────────────────

- The corpus PDFs are NOT uploaded (1.2 GB; would take 10-20 minutes).
- Endpoints that need PDFs (``/documents/{src}/{id}/pdf`` and ``/extract``)
  will return 404. ``/search`` and ``/documents`` work fine.
- To enable the PDF endpoints, also run:
       modal volume put velix-data corpus_glo /corpus_glo
       modal volume put velix-data corpus_sec /corpus_sec
  ...and update the manifest file_path values to point at the Linux paths
  (``/data/corpus_glo/...``).

──────────────────────────────────────────────────────────────────────────────
GPU activation (later)
──────────────────────────────────────────────────────────────────────────────

To swap the mocks for real models, change ``use_mock_*`` to False in the
``AppConfig`` below, add the GPU-side packages to the image, and request
GPU on the function::

    image = (
        modal.Image.debian_slim(python_version="3.12")
        .pip_install(..., "torch>=2.2.0", "transformers>=4.45.0",
                     "colpali-engine>=0.3.0", "accelerate>=0.30.0")
        .add_local_python_source("velix")
    )

    @app.function(image=image, gpu="A10G", volumes={"/data": data_volume}, ...)

Cold-start hint: pre-load the models into a snapshot::

    image = image.run_function(preload_models)

…where ``preload_models`` triggers ``ColQwen2Embedder()`` and
``Qwen2VLExtractor()`` instantiation so weights are baked into the snapshot.
"""

from pathlib import Path

import modal

# ─────────────────────────────────────────────────────────────────────────
# App + image
# ─────────────────────────────────────────────────────────────────────────

app = modal.App("velix")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Core
        "pymupdf>=1.24.0",
        "pydantic>=2.6.0",
        "pillow>=10.0.0",
        "numpy>=1.26.0",
        "rich>=13.7.0",
        "typer>=0.12.0",
        "python-dotenv>=1.0.0",
        "rapidfuzz>=3.9.0",
        # Retrieval (CPU-side; GPU-side adds torch + colpali-engine later)
        "qdrant-client>=1.10.0",
        # API
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "aiosqlite>=0.20.0",
        "python-multipart>=0.0.12",
    )
    .add_local_python_source("velix")
)

# Persistent volume for the Qdrant index and manifests. Survives across
# deploys; updates via `modal volume put`.
data_volume = modal.Volume.from_name("velix-data", create_if_missing=True)


# ─────────────────────────────────────────────────────────────────────────
# Web endpoint
# ─────────────────────────────────────────────────────────────────────────


@app.function(
    image=image,
    volumes={"/data": data_volume},
    timeout=300,
    min_containers=0,    # scales to zero when idle
    max_containers=10,
)
@modal.asgi_app(label="velix-api")
def fastapi_app():
    from velix.api.app import create_app
    from velix.api.deps import AppConfig

    config = AppConfig(
        manifest_paths=[
            Path("/data/manifests/corpus_glo.csv"),
            Path("/data/manifests/corpus_sec.csv"),
        ],
        qdrant_target="/data/velix_index",
        cache_db_path=Path("/data/velix_api_cache.sqlite"),
        use_mock_embedder=True,
        use_mock_extractor=True,
        # Locked open during the demo. Lock down to your Netlify origin
        # post-launch by passing e.g. ["https://velix.netlify.app"].
        cors_origins=["*"],
        require_pdf=False,
    )
    return create_app(config)
