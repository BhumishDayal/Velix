"""Modal deployment for the Velix FastAPI service.

Deploys the same FastAPI app from ``src/velix/api/`` as a serverless web
endpoint on Modal. Uses real ColQwen2 (visual retrieval) and Qwen2.5-VL-7B
(structured extraction) models on an A10G GPU. Scales to zero when idle.

──────────────────────────────────────────────────────────────────────────────
Deployment workflow
──────────────────────────────────────────────────────────────────────────────

Prerequisites:
    pip install modal
    modal token new                                              # one-time
    modal volume create velix-data

Build the index ON A GPU (Kaggle T4 free, or Modal/RunPod paid):
    See the Kaggle notebook flow in the README.
    Result: a velix_index/ folder you download as a tarball.

Upload the index + manifests + PDFs to the volume:
    modal volume rm velix-data /velix_index --recursive  # if replacing an old one
    modal volume put velix-data velix_index /velix_index
    modal volume put velix-data corpus_glo_modal.csv /manifests/corpus_glo.csv --force
    modal volume put velix-data corpus_sec_modal.csv /manifests/corpus_sec.csv --force
    modal volume put velix-data corpus_glo /corpus_glo
    modal volume put velix-data corpus_sec /corpus_sec

Deploy:
    modal deploy modal_app.py

──────────────────────────────────────────────────────────────────────────────
Cold-start behavior
──────────────────────────────────────────────────────────────────────────────

Loading ColQwen2 + Qwen2.5-VL-7B from disk takes ~30-60s on first request
after idle. The ``scaledown_window`` setting keeps the container warm for
10 minutes after the last request, so realistic demo usage hits the cold
start at most once per visit.

For sub-5-second cold starts, swap the image to use ``image.run_function(
preload_models)`` so model weights are baked into a snapshot. Adds image
build time but eliminates the load delay. Skipped here to keep deploy fast.
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
        # Retrieval (CPU and GPU sides)
        "qdrant-client>=1.10.0",
        "torch>=2.2.0",
        "transformers>=4.45.0",
        "colpali-engine>=0.3.0",
        "accelerate>=0.30.0",
        # API
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "aiosqlite>=0.20.0",
        "python-multipart>=0.0.12",
    )
    .add_local_python_source("velix")
)

# Persistent volume for the Qdrant index, manifests, and corpus PDFs.
data_volume = modal.Volume.from_name("velix-data", create_if_missing=True)


# ─────────────────────────────────────────────────────────────────────────
# Web endpoint
# ─────────────────────────────────────────────────────────────────────────


@app.function(
    image=image,
    volumes={"/data": data_volume},
    gpu="A10G",                # 24 GB VRAM: ColQwen2 (~5 GB) + Qwen2.5-VL-7B (~14 GB) fit
    timeout=600,
    min_containers=0,           # scales to zero when idle
    max_containers=4,
    scaledown_window=600,       # keep container warm for 10 min after last request
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
        # Real models — GPU activated.
        use_mock_embedder=False,
        use_mock_extractor=False,
        # Locked open during the demo. Lock down to your Netlify origin
        # post-launch by passing e.g. ["https://velix01.netlify.app"].
        cors_origins=["*"],
        require_pdf=False,
    )
    return create_app(config)
