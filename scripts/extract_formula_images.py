#!/usr/bin/env python3
"""Render formula regions from a PDF using top-left PDF coordinates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pypdfium2 as pdfium


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf", type=Path)
    ap.add_argument("--regions", type=Path, required=True, help="JSON list or {regions:[...]} with id/page/box")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--scale", type=float, default=5.0)
    args = ap.parse_args()
    raw = json.loads(args.regions.read_text(encoding="utf-8"))
    regions = raw.get("regions", raw) if isinstance(raw, (dict, list)) else []
    doc = pdfium.PdfDocument(str(args.source_pdf))
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for item in regions:
        if item.get("kind", "formula") != "formula":
            continue
        page_number = int(item["page"])
        x0, y0, x1, y1 = map(float, item["box"])
        page = doc[page_number - 1]
        bitmap = page.render(scale=args.scale)
        image = bitmap.to_pil()
        crop = image.crop((round(x0 * args.scale), round(y0 * args.scale), round(x1 * args.scale), round(y1 * args.scale)))
        name = f"{item['id']}.png"
        crop.save(args.out / name)
        manifest.append({"id": item["id"], "page": page_number, "box": item["box"], "path": name, "width_px": crop.width, "height_px": crop.height, "display_width": item.get("display_width")})
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"formulas": len(manifest), "out": str(args.out.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
