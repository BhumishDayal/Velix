"""Corpus builder CLI.

Walks one or more source fetchers, downloads documents into the corpus
directory, and appends to the manifest. Resumable: documents already in the
manifest are skipped.

Usage:

    python scripts/corpus/build_corpus.py --source sec_edgar --max-docs 10 --out corpus

    python scripts/corpus/build_corpus.py --source sec_edgar --target-pages 1500 --out corpus
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# allow running as a script from the repo root without installing the package
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))

from corpus.fetchers.base import Fetcher  # noqa: E402
from corpus.fetchers.sec_edgar import SecEdgarFetcher  # noqa: E402
from corpus.fetchers.tx_glo import TexasGloFetcher  # noqa: E402
from corpus.manifest import Manifest, make_entry  # noqa: E402

FETCHER_REGISTRY: dict[str, type[Fetcher]] = {
    "sec_edgar": SecEdgarFetcher,
    "tx_glo": TexasGloFetcher,
}


def _build_fetcher(name: str, args: argparse.Namespace) -> Fetcher:
    cls = FETCHER_REGISTRY.get(name)
    if cls is None:
        raise SystemExit(
            f"unknown source '{name}'. available: {sorted(FETCHER_REGISTRY)}"
        )
    kwargs: dict[str, object] = {}
    if name == "tx_glo":
        if args.start_id is not None:
            kwargs["start_id"] = args.start_id
        if args.end_id is not None:
            kwargs["end_id"] = args.end_id
    return cls(**kwargs)


def run(
    source: str,
    *,
    out_dir: Path,
    max_docs: int | None,
    target_pages: int | None,
    args: argparse.Namespace,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(out_dir)

    print(f"corpus root: {out_dir}")
    print(f"existing manifest: {len(manifest._seen_ids)} docs, "
          f"{manifest.total_pages()} pages")
    print(f"source: {source}, max_docs={max_docs}, target_pages={target_pages}")

    discover_cap = max_docs if max_docs is not None else 10_000
    pages_added = 0
    docs_added = 0

    with _build_fetcher(source, args) as fetcher:
        for task in fetcher.discover(discover_cap):
            if manifest.has(fetcher.source_name, task.source_id):
                continue
            dest = out_dir / task.relative_path
            try:
                fetcher.download(task.url, dest)
            except Exception as exc:
                print(f"  ✗ {task.source_id}: {exc.__class__.__name__}: {exc}")
                continue
            entry = make_entry(
                source=fetcher.source_name,
                source_id=task.source_id,
                file_path=dest,
                content_type=task.content_type,
                title=task.title,
                metadata_json=json.dumps(task.metadata or {}),
            )
            manifest.append(entry)
            docs_added += 1
            pages_added += entry.page_count
            print(f"  ✓ {task.source_id}  ({entry.page_count}p)")
            if target_pages is not None and pages_added >= target_pages:
                break

    print(
        f"\ndone. added {docs_added} docs, {pages_added} pages."
        f" corpus total: {manifest.total_pages()} pages across "
        f"{sum(manifest.count_by_source().values())} docs "
        f"({manifest.count_by_source()})."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Velix demo corpus.")
    parser.add_argument(
        "--source",
        required=True,
        choices=sorted(FETCHER_REGISTRY),
        help="Which source fetcher to run.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("corpus"),
        help="Corpus root directory (default: ./corpus)",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Hard cap on number of documents discovered.",
    )
    parser.add_argument(
        "--target-pages",
        type=int,
        default=None,
        help="Stop fetching once this many pages have been added this run.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=None,
        help="(tx_glo only) First grant ID to probe.",
    )
    parser.add_argument(
        "--end-id",
        type=int,
        default=None,
        help="(tx_glo only) Stop probing at this grant ID (exclusive).",
    )
    args = parser.parse_args()

    run(
        source=args.source,
        out_dir=args.out,
        max_docs=args.max_docs,
        target_pages=args.target_pages,
        args=args,
    )


if __name__ == "__main__":
    main()
