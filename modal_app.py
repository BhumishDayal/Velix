"""Modal deployment for the Velix FastAPI service. See README for setup."""

from pathlib import Path

import modal

app = modal.App("velix")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "pymupdf>=1.24.0",
        "pydantic>=2.6.0",
        "pillow>=10.0.0",
        "numpy>=1.26.0",
        "rich>=13.7.0",
        "typer>=0.12.0",
        "python-dotenv>=1.0.0",
        "rapidfuzz>=3.9.0",
        "qdrant-client>=1.10.0",
        "torch>=2.2.0",
        "transformers>=4.45.0",
        "colpali-engine>=0.3.0",
        "accelerate>=0.30.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "aiosqlite>=0.20.0",
        "python-multipart>=0.0.12",
    )
    .add_local_python_source("velix")
)

data_volume = modal.Volume.from_name("velix-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/data": data_volume},
    gpu="A10G",
    timeout=600,
    min_containers=0,
    max_containers=4,
    scaledown_window=600,
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
        use_mock_embedder=False,
        use_mock_extractor=False,
        cors_origins=["*"],
        require_pdf=False,
    )
    return create_app(config)
