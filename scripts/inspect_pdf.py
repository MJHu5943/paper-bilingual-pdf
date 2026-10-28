#!/usr/bin/env python3
"""Inspect a source PDF before translation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader


def annotation_info(page):
    out = []
    for ref in page.get("/Annots") or []:
        obj = ref.get_object()
        action = obj.get("/A")
        out.append({
            "subtype": str(obj.get("/Subtype", "")),
            "rect": [float(v) for v in obj.get("/Rect", [])],
            "action": str(action.get("/S", "")) if action else "",
            "uri": str(action.get("/URI", "")) if action and action.get("/URI") else "",
            "destination": str(obj.get("/Dest", "")) if obj.get("/Dest") else "",
        })
    return out


def image_count(page):
    resources = page.get("/Resources") or {}
    xobjects = resources.get("/XObject") or {}
    count = 0
    for ref in xobjects.values():
        try:
            if ref.get_object().get("/Subtype") == "/Image":
                count += 1
        except Exception:
            continue
    return count


def inspect(path: Path):
    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        annots = annotation_info(page)
        pages.append({
            "page": number,
            "width": float(page.mediabox.width),
            "height": float(page.mediabox.height),
            "text_chars": len(text),
            "text_preview": text[:500],
            "images": image_count(page),
            "annotations": annots,
            "annotation_count": len(annots),
        })
    return {
        "source_pdf": str(path.resolve()),
        "pages": pages,
        "page_count": len(pages),
        "total_text_chars": sum(p["text_chars"] for p in pages),
        "total_annotations": sum(p["annotation_count"] for p in pages),
        "total_uri_links": sum(bool(a["uri"]) for p in pages for a in p["annotations"]),
        "total_goto_links": sum(a["action"] == "/GoTo" for p in pages for a in p["annotations"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    data = inspect(args.source_pdf)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: data[k] for k in ("page_count", "total_text_chars", "total_annotations", "total_uri_links", "total_goto_links")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
