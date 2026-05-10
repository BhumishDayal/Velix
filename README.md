# Velix

A research project on visual-first retrieval and structured extraction for
legal and real-asset documents. The corpus, retrieval scaffolding, schema-typed
extraction, and the marketing site are built. The hosted API and the
in-product UI are next.

This is an open-source experiment, not a commercial product.

## Status

| Phase | What | State |
|---|---|---|
| 0 | Tier-routing OCR pipeline + domain validators | shipped |
| 1 | Public oil & gas corpus (194 docs / 3,844 pages) | shipped |
| 2 | Visual retrieval (ColQwen2 + Qdrant multi-vector) | scaffolding shipped, GPU activation pending |
| 3 | Structured extraction (Qwen2.5-VL + Pydantic schemas) | scaffolding shipped, GPU activation pending |
| 4 | FastAPI backend on Modal | in progress |
| 5 | Next.js frontend on Netlify | landing page shipped, app screens next |

**56 tests, all passing.** Run `pytest` to see for yourself.

## Why

Most legal-document AI pipelines are built on the same shape: OCR every page,
parse the text with regex or an LLM, store the parse, search the parse. That
shape was right when OCR was the only tool available. It's increasingly the
wrong shape.

Visual-language models can index a page directly, without OCR, with embeddings
that survive the kind of layout, handwriting, and stamp noise that breaks OCR.
Pydantic + JSON-mode VLM output gives you typed extraction without the
parse step. Combine those two, and you get a system where:

- The expensive operation (full extraction) runs only on pages a user
  actually queries — typically a small fraction of the corpus.
- The cheap operation (visual indexing) runs once per page and produces
  embeddings that work on tables, signatures, and 1850s manuscript scans.
- Domain validators (PLSS land descriptions, mineral fractions, grantor →
  grantee chains) sit inside the extraction schemas as field-level type
  constraints, not as a flaky post-processing pass.

That's what Velix is.

## Architecture

```
┌────────────────────┐         ┌──────────────────────┐
│  Public corpus     │         │ Frontend (Next.js)   │
│  SEC + Texas GLO   │         │ velix.netlify.app    │
│  3,844 pages       │         └─────────┬────────────┘
└──────────┬─────────┘                   │
           │ corpus build                │ HTTPS
           ▼                             ▼
┌──────────────────────────────────────────────────────────┐
│ FastAPI backend (in progress, hosted on Modal)           │
│                                                          │
│  GET /search        → query → ColQwen2 → Qdrant MaxSim   │
│  POST /extract      → page image → Qwen2.5-VL → Pydantic │
│  GET  /documents    → corpus browse                      │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ Storage                                                  │
│  Qdrant — multi-vector index of every page's embeddings  │
│  SQLite — extraction cache (one row per typed field set) │
│  Filesystem — original PDFs                              │
└──────────────────────────────────────────────────────────┘
```

Inside `src/velix/`:

```
config.py              Env-driven settings
models/                Pydantic types passed between tiers
validators/            PLSS, mineral fractions, grantor→grantee chain checks
pipeline/              Tier-routing OCR fallback (Tier 0–3)
retrieval/             ColQwen2 embedder + Qdrant MaxSim index
extraction/            Pydantic schemas + Qwen2.5-VL extractor
api/                   FastAPI service [in progress]
cli.py                 typer CLI (extract, cost-compare, index, search,
                       extract-fields, serve)
```

Inside `web/`: Next.js 15 + Tailwind + Framer Motion landing page,
deployed to Netlify.

Inside `scripts/corpus/`: the fetcher modules that built `corpus_sec/` and
`corpus_glo/` from SEC EDGAR and the Texas General Land Office.

## Setup

Conda is the path of least resistance on Windows; use whatever you like.

```powershell
conda create -n velix python=3.12 -y
conda activate velix
pip install -e ".[dev]"
pytest -v
```

That installs the core package + pytest. All 56 tests should pass in under
five seconds, no GPU required.

The optional extras enable specific features:

```powershell
pip install -e ".[paddle]"      # Tier 1 OCR (PaddleOCR)
pip install -e ".[olmocr]"      # Tier 2 OCR (olmOCR-2, GPU)
pip install -e ".[claude]"      # Tier 3 OCR (Anthropic Vision API)
pip install -e ".[retrieval]"   # ColQwen2 + Qdrant (GPU)
pip install -e ".[corpus]"      # corpus fetchers (httpx, bs4, tqdm)
```

## Usage

A few of the CLI commands you'll actually run.

**Run the tier OCR pipeline on a single PDF:**

```powershell
velix extract path\to\document.pdf
```

**Show projected savings vs Textract:**

```powershell
velix cost-compare path\to\document.pdf --volume 1000000
```

**Build a corpus slice from public oil & gas archives** (resumable; skip
files already in the manifest):

```powershell
python scripts\corpus\build_corpus.py --source sec_edgar --target-pages 1500 --out corpus_sec
python scripts\corpus\build_corpus.py --source tx_glo --start-id 9100 --end-id 25000 --target-pages 2000 --out corpus_glo
```

**Index the corpus into Qdrant** using the mock embedder (CPU) for testing,
or the real ColQwen2 (GPU) for production:

```powershell
velix index --manifest corpus_glo\manifest.csv --index velix_index --mock
velix index --manifest corpus_glo\manifest.csv --index velix_index    # GPU
```

**Search the index:**

```powershell
velix search "Dallas County mineral grant" --index velix_index --mock
```

**Extract typed fields from a single page** with one of the six document
schemas:

```powershell
velix extract-fields path\to\deed.pdf --schema mineral_deed --page 0 --mock
velix extract-fields path\to\deed.pdf --schema oil_gas_lease --page 0
```

Schemas: `mineral_deed`, `oil_gas_lease`, `division_order`, `assignment`,
`ratification`, `joa_snippet`.

## Configuration

Copy `.env.example` to `.env`. Knobs you'll touch:

- `TIER1_CONFIDENCE_THRESHOLD` (default `0.85`) — text-layer pages above this skip Tier 1.
- `TIER2_CONFIDENCE_THRESHOLD` (default `0.92`) — PaddleOCR pages above this skip Tier 2.
- `TIER3_CONFIDENCE_THRESHOLD` (default `0.80`) — olmOCR pages above this skip Tier 3.
- `TIER3_ENABLED` (default `false`) — set `true` to allow Claude vision escalation.
- `TIER2_OLMOCR_DEVICE` (default `cuda`) — `cpu` to load on CPU (very slow).
- `ANTHROPIC_API_KEY` — required if you enable Tier 3.

## Tests

```powershell
pytest -v
```

What's covered (56 tests, all green):

- Validators — PLSS, mineral fractions, grantor/grantee chain consistency
  (incl. fuzzy matching with rapidfuzz to survive OCR noise).
- Pipeline orchestrator — Tier 0 short-circuit, full Tier 0→3 escalation,
  Tier 3 threshold blocks unnecessary Claude calls, Tier 3 disabled
  fallback, missing-PDF errors.
- Retrieval — Qdrant collection schema, multi-vector upsert/search,
  idempotent re-upsert via UUID5 keys, source filtering, dimension
  validation, full corpus pipeline.
- Extraction — round-trip parsing through the existing validators, schema
  rejection of out-of-range values, MockExtractor produces a valid
  instance for every doc type.

## Corpus

The repo doesn't ship the corpus PDFs (they total ~1.2 GB and are
regeneratable). Build it yourself with the `scripts/corpus/build_corpus.py`
commands above. The `manifest.csv` files that result carry full provenance
per row (source, source_id, sha256, page_count, plus source-specific
metadata like county, grantee, patent date, CIK, accession number).

Sources:

- **SEC EDGAR** — modern oil & gas company filings (10-K, 10-Q, 8-K, S-1,
  S-11, DEF 14A) filtered by SIC 1311. Polite scraping at 1 req/sec.
- **Texas General Land Office** — historical land grants from 1840s–1900s.
  Many are scanned manuscripts, often handwritten in Spanish or
  Republic-era English. The hard cases that motivate visual retrieval.
- **BLM-GLO** — federal land patents from OK / NM / WY. Stub fetcher
  only; the BLM site loads patent images via JavaScript and would need
  Playwright or a reverse-engineered endpoint. Not on the critical path.

## What's not built

Worth being explicit about, since the README's job is to set expectations:

- The hosted demo URL doesn't exist yet. The FastAPI service is being
  scaffolded; the Modal deployment is the next step.
- ColQwen2 has not been activated against the real corpus. The retrieval
  pipeline is end-to-end exercised with a deterministic mock embedder
  for tests; the real GPU run is a one-shot Kaggle session.
- The frontend is the public landing page only. Upload, document viewer,
  and search UI screens come once the API is live.

## License

MIT. See LICENSE.

---

Built by [Bhumish Dayal](https://github.com/bhumishdayal).
