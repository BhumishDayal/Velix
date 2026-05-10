"""End-to-end smoke test: generate a tiny PDF, run the pipeline, print result."""

from pathlib import Path

import pymupdf

from velix.pipeline import Pipeline


def main() -> None:
    test_pdf = Path("tmp_smoketest.pdf")
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), "MINERAL DEED")
    page.insert_text((50, 130), "Grantor: Smith Family Trust")
    page.insert_text((50, 150), "Grantee: ABC Minerals LLC")
    page.insert_text((50, 180), "An undivided 1/64 interest in:")
    page.insert_text((50, 200), "NE/4 of SE/4, Section 12, T5N, R7W")
    doc.save(test_pdf)
    doc.close()

    try:
        pipeline = Pipeline()
        result = pipeline.run(test_pdf)
        print(f"pages={result.page_count}")
        print(f"tiers_used={[t.value for t in result.tiers_used]}")
        print(f"total_cost=${result.total_cost_usd:.5f}")
        print(f"overall_confidence={result.overall_confidence:.2f}")
        print(f"page_0_tier={result.pages[0].tier.value}")
        print(f"page_0_chars={len(result.pages[0].raw_text)}")
        print("page_0_text:")
        print(result.pages[0].raw_text)
    finally:
        test_pdf.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
