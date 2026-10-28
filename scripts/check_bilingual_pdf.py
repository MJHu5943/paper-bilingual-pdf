#!/usr/bin/env python3
"""Check structural invariants of a generated bilingual PDF."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader


def annotation_count(reader):
    return sum(len(page.get("/Annots") or []) for page in reader.pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf", type=Path)
    ap.add_argument("output_pdf", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    source = PdfReader(str(args.source_pdf))
    output = PdfReader(str(args.output_pdf))
    source_text = sum(len(page.extract_text() or "") for page in source.pages)
    output_text = sum(len(page.extract_text() or "") for page in output.pages)
    source_annots = annotation_count(source)
    output_annots = annotation_count(output)
    source_uri = sum(1 for page in source.pages for ref in (page.get("/Annots") or []) if ref.get_object().get("/A") and ref.get_object().get("/A").get("/URI"))
    output_uri = sum(1 for page in output.pages for ref in (page.get("/Annots") or []) if ref.get_object().get("/A") and ref.get_object().get("/A").get("/URI"))
    expected_width = float(source.pages[0].mediabox.width) * 2 + 42
    expected_height = float(source.pages[0].mediabox.height) + 44
    checks = {
        "page_count_equal": len(source.pages) == len(output.pages),
        "spread_width_equal": abs(float(output.pages[0].mediabox.width) - expected_width) < 0.1,
        "spread_height_equal": abs(float(output.pages[0].mediabox.height) - expected_height) < 0.1,
        "source_text_present": output_text > source_text,
        "annotations_not_lost": output_annots >= source_annots,
        "uri_links_not_lost": output_uri >= source_uri,
        "first_page_has_text": bool(output.pages[0].extract_text()),
    }
    result = {"source_pages": len(source.pages), "output_pages": len(output.pages), "source_text_chars": source_text, "output_text_chars": output_text, "source_annotations": source_annots, "output_annotations": output_annots, "source_uri_links": source_uri, "output_uri_links": output_uri, "checks": checks, "ok": all(checks.values())}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
