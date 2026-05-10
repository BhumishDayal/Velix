# Velix

Tiered, confidence-gated document extraction with hybrid retrieval, built for
high-volume legal and real-asset workflows. Velix decides which OCR engine to
run on each page based on document quality, validates the result against the
structure of legal land descriptions, mineral interest fractions, and
grantor/grantee chains, and exposes the corpus through a hybrid BM25 +
semantic search layer.

## Why this exists

Generic OCR pipelines run AWS Textract Analyze on every page (~$50/1000)
regardless of whether the page already has a clean text layer. For modern
legal PDFs the majority of pages do. Velix's value proposition is threefold:

1. **Cost** — route each page to the cheapest tier that can extract it
   accurately, not the most expensive one by default.
2. **Accuracy where it matters** — character-level OCR accuracy is largely
   solved; the silent errors that hurt royalty math come from misread mineral
   fractions, broken chain-of-title party names, and malformed legal land
   descriptions. Velix validates those specifically.
3. **Findability** — extracted clauses are useless if you can't query them.
   A hybrid retrieval layer (BM25 lexical + dense semantic) sits on top so
   "find every indemnification clause across 2M pages" runs in milliseconds.

## Tiered extraction pipeline

| Tier | Engine | When it runs | Cost / 1M pages |
|------|--------|--------------|----------------|
| 0 | `pymupdf` text-layer probe | Always tried first. Wins for any digitally-generated PDF. | ~$0 |
| 1 | PaddleOCR 3.0 (self-hosted) | Tier 0 confidence below threshold. Strong on tables/forms. | ~$90–141 |
| 2 | olmOCR 2 (Allen AI, self-hosted VLM) | Tier 1 confidence below threshold. Fine-tuned on legal docs. | ~$176 |
| 3 | Claude Sonnet 4.6 Vision | Opt-in escalation for legally critical pages only. | ~$10,000 |

Compare to AWS Textract Analyze at **~$50,000 per million pages**. At 1M
pages/month volume that is a $600K/year line item; Velix targets a 5–25×
reduction depending on the document mix.

## Layout

```
src/velix/
├── config.py                        # env-driven settings
├── models/extraction.py             # Pydantic types passed between tiers
├── validators/
│   ├── land_description.py          # PLSS Section/Township/Range parser
│   ├── mineral_fraction.py          # 1/64, 5/192, decimal, word forms
│   └── party_consistency.py         # grantee→grantor chain checker
├── pipeline/
│   ├── base.py                      # TierExtractor ABC
│   ├── rendering.py                 # PDF → image helpers
│   ├── tier0_pdf.py                 # text-layer probe
│   ├── tier1_paddle.py              # PaddleOCR (deferred import)
│   ├── tier2_olmocr.py              # olmOCR 2 via transformers (deferred)
│   ├── tier3_claude.py              # Claude vision (deferred)
│   └── orchestrator.py              # confidence-gated routing
└── cli.py                           # `extract` and `cost-compare` commands

tests/                               # validator unit tests (20 tests, all passing)
scripts/smoketest.py                 # generate a PDF and run the pipeline
```

## Quickstart (conda)

```powershell
conda create -n velix python=3.12 -y
conda activate velix
pip install -e .
pytest                         # 20 passing
python scripts\smoketest.py
velix cost-compare your.pdf --volume 1000000
```

To enable the heavier tiers, install the extras:

```powershell
pip install -e ".[paddle]"     # Tier 1
pip install -e ".[olmocr]"     # Tier 2 (needs GPU)
pip install -e ".[claude]"     # Tier 3 (needs API key)
pip install -e ".[search]"     # Hybrid retrieval (BM25 + sentence-transformers + Qdrant)
```

## Configuration

Copy `.env.example` to `.env`. Key knobs:

- `TIER1_CONFIDENCE_THRESHOLD` (default `0.85`) — text-layer pages above this skip Tier 1.
- `TIER2_CONFIDENCE_THRESHOLD` (default `0.92`) — PaddleOCR pages above this skip Tier 2.
- `TIER3_CONFIDENCE_THRESHOLD` (default `0.80`) — olmOCR pages above this skip Tier 3 (no Claude escalation).
- `TIER3_ENABLED` (default `false`) — set `true` to allow Claude vision escalation.
- `TIER2_OLMOCR_DEVICE` (default `cuda`) — set to `cpu` to load model on CPU (slow).
- `ANTHROPIC_API_KEY` — required for Tier 3.

## Roadmap

- **Phase 2 — Backend**: FastAPI service, Postgres schema for extractions and
  audit logs, Celery + Redis async job queue, JWT/SSO auth scaffolding.
- **Phase 3 — Hybrid retrieval**: BM25 (`rank-bm25`) lexical index +
  sentence-transformer dense index in Qdrant; reciprocal rank fusion at query
  time; clause-level chunking with bbox-anchored citations so every search
  hit links back to the source pixels.
- **Phase 4 — Frontend**: Next.js + shadcn/ui with PDF viewer, bbox
  highlighting, review queue for low-confidence extractions, and a search UI
  scoped to a corpus or a single document.
- **Phase 5 — Deploy**: Docker Compose to a GPU VPS, sample public-domain
  document corpus, end-to-end demo video.

## Honest caveats

- The Tier 2 (olmOCR) confidence score is a heuristic on output length;
  production use should add a second-pass check or domain-validator-driven
  re-scoring.
- The party consistency checker uses token overlap, not edit distance — good
  enough to catch chain breaks, not robust to OCR garbage in names. Plug in
  `rapidfuzz` if the corpus has noisy names.
- The 100% savings reading on a single text-layer PDF in `cost-compare` is an
  artifact of that document; real corpora will hit Tier 1+ on a meaningful
  slice.
