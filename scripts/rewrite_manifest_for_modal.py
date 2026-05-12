"""Rewrite a corpus manifest CSV's file_path column for Modal Volume paths.

Local manifests carry Windows-style relative paths like
``corpus_glo\\tx_glo\\9113.pdf``. On Modal those PDFs live under the volume
mount at ``/data/corpus_glo/tx_glo/9113.pdf``. This script normalizes
backslashes and prefixes the mount path. Idempotent: rows already
absolute (start with ``/``) are left alone.

Usage:
    python scripts/rewrite_manifest_for_modal.py corpus_glo/manifest.csv corpus_glo_modal.csv
    python scripts/rewrite_manifest_for_modal.py corpus_sec/manifest.csv corpus_sec_modal.csv

Optional:
    --prefix data    Volume mount inside the container (default: data).
"""

from __future__ import annotations

import argparse
import csv
import sys


def linux_path(raw: str, prefix: str) -> str:
    if raw.startswith("/"):
        return raw  # already absolute Linux
    parts = raw.replace("\\", "/").lstrip("/").split("/")
    return "/" + "/".join([prefix.strip("/"), *parts])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", help="Source manifest CSV path")
    parser.add_argument("output", help="Destination manifest CSV path")
    parser.add_argument(
        "--prefix",
        default="data",
        help="Volume mount inside the container (default: data → /data/...)",
    )
    args = parser.parse_args()

    with open(args.input, encoding="utf-8", newline="") as fin, open(
        args.output, "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames or []
        if "file_path" not in fieldnames:
            print(
                f"error: input manifest has no 'file_path' column "
                f"(found: {fieldnames})",
                file=sys.stderr,
            )
            return 2
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        rewritten = 0
        for row in reader:
            row["file_path"] = linux_path(row["file_path"], args.prefix)
            writer.writerow(row)
            rewritten += 1

    print(f"wrote {args.output} ({rewritten} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
