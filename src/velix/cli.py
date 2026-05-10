"""CLI entry point. Run a PDF through the pipeline and show a cost comparison."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

if sys.platform == "win32":
    # rich emits punctuation (·, —) Windows cp1252 can't encode; force UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from velix.models import DocumentExtraction, Tier
from velix.pipeline import Pipeline

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()

TEXTRACT_ANALYZE_COST_PER_PAGE = 0.05
TEXTRACT_DETECT_COST_PER_PAGE = 0.0015


def _build_embedder(use_mock: bool):
    if use_mock:
        from velix.retrieval import MockEmbedder

        return MockEmbedder()
    from velix.retrieval.embedder import ColQwen2Embedder

    return ColQwen2Embedder()


@app.command()
def extract(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    output_json: Path | None = typer.Option(None, "--json", help="Write extraction to JSON"),
    enable_tier3: bool = typer.Option(False, "--tier3", help="Allow Claude vision escalation"),
) -> None:
    """Extract a single PDF and print a per-page tier + cost summary."""

    pipeline = Pipeline(enable_tier3=enable_tier3)
    document = pipeline.run(pdf_path)

    _print_summary(document)
    if output_json:
        output_json.write_text(document.model_dump_json(indent=2))
        console.print(f"\n[dim]wrote extraction to[/] {output_json}")


@app.command()
def cost_compare(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    monthly_volume: int = typer.Option(
        1_000_000,
        "--volume",
        help="Pages per month to extrapolate cost savings against",
    ),
    enable_tier3: bool = typer.Option(False, "--tier3"),
) -> None:
    """Run the pipeline and show monthly $ savings vs Textract."""

    pipeline = Pipeline(enable_tier3=enable_tier3)
    document = pipeline.run(pdf_path)

    pages = max(document.page_count, 1)
    pipeline_cost_per_page = document.total_cost_usd / pages

    annual_pipeline = pipeline_cost_per_page * monthly_volume * 12
    annual_textract_analyze = TEXTRACT_ANALYZE_COST_PER_PAGE * monthly_volume * 12
    annual_textract_detect = TEXTRACT_DETECT_COST_PER_PAGE * monthly_volume * 12

    table = Table(title=f"Cost projection at {monthly_volume:,} pages/month")
    table.add_column("Pipeline")
    table.add_column("Per-page", justify="right")
    table.add_column("Annual", justify="right")
    table.add_column("Savings vs Analyze", justify="right")

    table.add_row(
        "Velix tiered (this build)",
        f"${pipeline_cost_per_page:.5f}",
        f"${annual_pipeline:,.0f}",
        f"-${annual_textract_analyze - annual_pipeline:,.0f}",
    )
    table.add_row(
        "AWS Textract Analyze (forms/tables)",
        f"${TEXTRACT_ANALYZE_COST_PER_PAGE:.5f}",
        f"${annual_textract_analyze:,.0f}",
        "—",
    )
    table.add_row(
        "AWS Textract Detect Text only",
        f"${TEXTRACT_DETECT_COST_PER_PAGE:.5f}",
        f"${annual_textract_detect:,.0f}",
        f"-${annual_textract_analyze - annual_textract_detect:,.0f}",
    )

    _print_summary(document)
    console.print()
    console.print(table)

    if annual_textract_analyze > 0:
        savings_pct = (
            (annual_textract_analyze - annual_pipeline) / annual_textract_analyze * 100
        )
        console.print(
            f"\n[bold green]Savings vs Textract Analyze: {savings_pct:.1f}%[/bold green]"
        )


def _print_summary(document: DocumentExtraction) -> None:
    tier_counts: Counter[Tier] = Counter(p.tier for p in document.pages)
    duration_total = sum(p.duration_ms for p in document.pages)

    table = Table(title=f"Extraction summary — {Path(document.source_path).name}")
    table.add_column("Page", justify="right")
    table.add_column("Tier")
    table.add_column("Confidence", justify="right")
    table.add_column("Chars", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Duration", justify="right")

    for page in document.pages:
        table.add_row(
            str(page.page_number),
            page.tier.value,
            f"{page.confidence:.2f}",
            str(len(page.raw_text)),
            f"${page.cost_usd:.5f}",
            f"{page.duration_ms} ms",
        )

    console.print(table)
    console.print(
        f"\n[bold]{document.page_count}[/bold] pages · "
        f"total cost [bold]${document.total_cost_usd:.4f}[/bold] · "
        f"total time [bold]{duration_total} ms[/bold] · "
        f"overall confidence [bold]{document.overall_confidence:.2f}[/bold]"
    )

    breakdown = ", ".join(
        f"{tier.value}={count}" for tier, count in tier_counts.most_common()
    )
    console.print(f"[dim]tier breakdown: {breakdown}[/dim]")


@app.command()
def index(
    manifest: list[Path] = typer.Option(
        ...,
        "--manifest",
        "-m",
        help="Path to one or more corpus manifest CSVs (repeat the flag).",
    ),
    index_path: Path = typer.Option(
        Path("velix_index"),
        "--index",
        help="Qdrant target: a directory path (file-backed), 'memory', or http(s)://host URL.",
    ),
    use_mock: bool = typer.Option(
        False,
        "--mock",
        help="Use the MockEmbedder (CPU, deterministic) instead of ColQwen2.",
    ),
    batch_size: int = typer.Option(4, "--batch-size", min=1),
) -> None:
    """Render every PDF in the manifest(s) and upsert page embeddings into the index."""

    from velix.retrieval import VelixIndex
    from velix.retrieval.index import make_qdrant_client
    from velix.retrieval.pipeline import index_corpus

    embedder = _build_embedder(use_mock)
    client = make_qdrant_client(index_path)
    velix_index = VelixIndex(client, embedding_dim=embedder.embedding_dim)

    console.print(
        f"indexing into [bold]{index_path}[/bold] "
        f"({'mock' if use_mock else 'ColQwen2'} embedder, "
        f"dim={embedder.embedding_dim})"
    )
    stats = index_corpus(
        manifest_paths=manifest,
        embedder=embedder,
        index=velix_index,
        batch_size=batch_size,
    )
    console.print(
        f"[green]done.[/green] {stats['docs']} docs, {stats['pages']} pages indexed; "
        f"{stats['skipped_missing_pdf']} skipped (missing pdf). "
        f"index size: {velix_index.count()} points."
    )


@app.command()
def search(
    query: str = typer.Argument(..., help="Natural-language search query"),
    index_path: Path = typer.Option(
        Path("velix_index"),
        "--index",
        help="Qdrant target: a directory path (file-backed), 'memory', or http(s)://host URL.",
    ),
    limit: int = typer.Option(10, "--limit", "-k", min=1, max=100),
    source: str | None = typer.Option(
        None, "--source", help="Filter to one corpus source (e.g. 'tx_glo')."
    ),
    use_mock: bool = typer.Option(
        False,
        "--mock",
        help="Use the MockEmbedder (must match the embedder used for indexing).",
    ),
) -> None:
    """Run a hybrid visual search over the indexed corpus."""

    from velix.retrieval import VelixIndex
    from velix.retrieval.index import make_qdrant_client

    embedder = _build_embedder(use_mock)
    client = make_qdrant_client(index_path)
    velix_index = VelixIndex(client, embedding_dim=embedder.embedding_dim)

    query_embedding = embedder.embed_query(query)
    hits = velix_index.search(query_embedding, limit=limit, source_filter=source)

    if not hits:
        console.print("[yellow]no hits.[/yellow]")
        return

    table = Table(title=f"top {len(hits)} for: {query!r}")
    table.add_column("#", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Source")
    table.add_column("Doc / Page")
    table.add_column("Title")
    for rank, hit in enumerate(hits, start=1):
        table.add_row(
            str(rank),
            f"{hit.score:.3f}",
            hit.source,
            f"{hit.source_id} p{hit.page_number}",
            hit.title or "—",
        )
    console.print(table)


@app.command()
def extract_fields(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    schema: str = typer.Option(
        ...,
        "--schema",
        help="Document schema name. One of: mineral_deed, oil_gas_lease, "
        "division_order, assignment, ratification, joa_snippet.",
    ),
    page: int = typer.Option(0, "--page", min=0, help="0-indexed page to extract."),
    use_mock: bool = typer.Option(
        False,
        "--mock",
        help="Use the MockExtractor (CPU, canned output) instead of Qwen2.5-VL.",
    ),
    output_json: Path | None = typer.Option(
        None, "--json", help="Write the extracted instance to JSON."
    ),
) -> None:
    """Extract typed fields from one PDF page using a schema-constrained VLM."""

    from velix.extraction import DOC_TYPE_REGISTRY, MockExtractor
    from velix.retrieval.page_rendering import render_pdf_pages

    schema_class = DOC_TYPE_REGISTRY.get(schema)
    if schema_class is None:
        console.print(
            f"[red]unknown schema '{schema}'. choices: "
            f"{sorted(DOC_TYPE_REGISTRY)}[/red]"
        )
        raise typer.Exit(code=1)

    if use_mock:
        extractor = MockExtractor()
    else:
        from velix.extraction.extractor import Qwen2VLExtractor

        extractor = Qwen2VLExtractor()

    target_image = None
    for page_number, image in render_pdf_pages(pdf_path):
        if page_number == page:
            target_image = image
            break
    if target_image is None:
        console.print(f"[red]page {page} not found in {pdf_path}[/red]")
        raise typer.Exit(code=1)

    instance = extractor.extract(target_image, schema_class, page_number=page)

    console.print(
        f"[bold]Extracted {schema_class.__name__}[/bold] "
        f"(p{page}, conf={instance.extraction_confidence:.2f}):"
    )
    console.print(instance.model_dump_json(indent=2))

    if output_json:
        output_json.write_text(instance.model_dump_json(indent=2))
        console.print(f"\n[dim]wrote extraction to[/] {output_json}")


@app.command()
def serve(
    manifest: list[Path] = typer.Option(
        ...,
        "--manifest",
        "-m",
        help="Path to one or more corpus manifest CSVs (repeat the flag).",
    ),
    qdrant: str = typer.Option(
        "memory",
        "--qdrant",
        help="Qdrant target: 'memory', a directory path, or http(s)://host URL.",
    ),
    cache_db: Path = typer.Option(
        Path("velix_api_cache.sqlite"),
        "--cache-db",
        help="SQLite file for the extraction cache.",
    ),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port", min=1, max=65535),
    use_mock: bool = typer.Option(
        False,
        "--mock",
        help="Use MockEmbedder + MockExtractor (CPU). Required for laptop dev.",
    ),
    cors_origin: list[str] = typer.Option(
        [],
        "--cors-origin",
        help="Allowed CORS origin (repeat the flag). Defaults to '*'.",
    ),
) -> None:
    """Run the FastAPI service locally with uvicorn."""

    import uvicorn

    from velix.api.app import create_app
    from velix.api.deps import AppConfig

    config = AppConfig(
        manifest_paths=list(manifest),
        qdrant_target=qdrant,
        cache_db_path=cache_db,
        use_mock_embedder=use_mock,
        use_mock_extractor=use_mock,
        cors_origins=list(cors_origin) if cors_origin else None,
    )
    api = create_app(config)
    console.print(
        f"[bold]starting Velix API[/bold] on http://{host}:{port}  "
        f"({'mock' if use_mock else 'real'} models, "
        f"{len(manifest)} manifest{'s' if len(manifest) != 1 else ''})"
    )
    uvicorn.run(api, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
