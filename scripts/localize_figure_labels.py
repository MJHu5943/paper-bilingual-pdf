#!/usr/bin/env python3
"""Replace explicitly mapped figure labels while preserving artwork and geometry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - depends on local PyMuPDF package name
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise SystemExit("需要 PyMuPDF：请在任务目录安装 PyMuPDF 后再运行此脚本。") from exc


def color(value):
    if isinstance(value, str) and value.startswith("#"):
        value = value[1:]
        return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    if isinstance(value, (list, tuple)):
        return tuple(float(v) for v in value)
    return (0, 0, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf", type=Path)
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--font", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--scale", type=float, default=5.0)
    args = ap.parse_args()
    spec = json.loads(args.regions.read_text(encoding="utf-8"))
    regions = spec.get("regions", spec) if isinstance(spec, (dict, list)) else []
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for region in regions:
        doc = fitz.open(str(args.source_pdf))
        page_number = int(region["page"])
        page = doc[page_number - 1]
        labels = region.get("labels", [])
        for label in labels:
            box = fitz.Rect(label["box"])
            page.add_redact_annot(box, fill=False, cross_out=False)
        # 只擦除文字，保留图像、线条和填充。
        page.apply_redactions(images=0, graphics=0, text=0)
        page.insert_font(fontname="cjk", fontfile=str(args.font))
        for label in labels:
            box = fitz.Rect(label["box"])
            translation = str(label["translation"])
            fontsize = float(label.get("size", max(4.0, box.height * 0.8)))
            page.insert_textbox(box, translation, fontname="cjk", fontsize=fontsize, color=color(label.get("color", "#000000")), align=int(label.get("align", 1)), rotate=int(label.get("rotate", 0)), overlay=True)
        crop = fitz.Rect(region["box"])
        out_pdf = args.out / f"{region['id']}.pdf"
        out_png = args.out / f"{region['id']}.png"
        clipped = fitz.open()
        clipped_page = clipped.new_page(width=crop.width, height=crop.height)
        clipped_page.show_pdf_page(clipped_page.rect, doc, page_number - 1, clip=crop)
        clipped.save(str(out_pdf), garbage=4, deflate=True)
        clipped_page.get_pixmap(matrix=fitz.Matrix(args.scale, args.scale), alpha=False).save(str(out_png))
        manifest.append({"id": region["id"], "page": page_number, "box": region["box"], "labels": len(labels), "pdf": str(out_pdf), "png": str(out_png)})
        clipped.close()
        doc.close()
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"regions": len(manifest), "out": str(args.out.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
