#!/usr/bin/env python3
"""Build a side-by-side, selectable bilingual PDF from a manifest."""
from __future__ import annotations

import argparse
import html
import json
import re
from io import BytesIO
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle


INK = colors.HexColor("#1a2f3b")
MUTED = colors.HexColor("#647986")
LINE = colors.HexColor("#d5dee3")


class Visual(Flowable):
    def __init__(self, item, root, max_width):
        super().__init__()
        self.item = item
        self.root = root
        self.path = (root / item["path"]).resolve()
        self.kind = item.get("kind", "png")
        if self.kind == "png":
            from PIL import Image
            with Image.open(self.path) as image:
                iw, ih = image.size
            natural_h = float(item.get("height", iw and ih * max_width / iw))
        else:
            page = PdfReader(str(self.path)).pages[0]
            iw, ih = float(page.mediabox.width), float(page.mediabox.height)
            natural_h = float(item.get("height", ih * max_width / iw))
        self.width = min(float(item.get("width", max_width)), max_width)
        self.height = natural_h if "height" in item else self.width * (natural_h / max_width if natural_h else 1)
        self.width = float(item.get("width", self.width))
        self.height = float(item.get("height", self.height))
        self.asset_id = item["id"]

    def draw(self):
        if self.kind == "png":
            self.canv.drawImage(ImageReader(str(self.path)), 0, 0, width=self.width, height=self.height, preserveAspectRatio=True, anchor="c", mask="auto")


def escape(text):
    return html.escape(text, quote=False).replace("\n", "<br/>")


def parse_blocks(markdown):
    lines = markdown.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        match = re.fullmatch(r"\[\[(FIGURE|TABLE|FORMULA):([^\]]+)\]\]", line)
        if match:
            blocks.append(("visual", match.group(1).lower(), match.group(2)))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in row):
                    rows.append(row)
                i += 1
            if rows:
                blocks.append(("table", rows))
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            blocks.append(("heading", len(heading.group(1)), heading.group(2)))
            i += 1
            continue
        if line.startswith("- "):
            blocks.append(("list", line[2:]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6})\s+|^\||^- |^\[\[", lines[i].strip()):
            paragraph.append(lines[i].strip())
            i += 1
        blocks.append(("paragraph", " ".join(paragraph)))
    return blocks


def inline(text):
    text = re.sub(r"`([^`]+)`", r"\1", text)
    parts = re.split(r"(\*\*.*?\*\*)", text)
    return "".join("<b>" + escape(part[2:-2]) + "</b>" if part.startswith("**") and part.endswith("**") else escape(part) for part in parts)


def make_flowables(blocks, assets, root, font_size, width):
    normal = ParagraphStyle("normal", fontName="CN", fontSize=font_size, leading=font_size * 1.52, textColor=INK, wordWrap="CJK", splitLongWords=True, firstLineIndent=font_size * 1.15, spaceAfter=font_size * 0.56)
    result = []
    for block in blocks:
        if block[0] == "paragraph":
            result.append(Paragraph(inline(block[1]), normal))
        elif block[0] == "heading":
            level = block[1]
            size = font_size * ({1: 1.42, 2: 1.2, 3: 1.08}.get(level, 1.0))
            style = ParagraphStyle("heading", parent=normal, fontName="CNBold", fontSize=size, leading=size * 1.28, firstLineIndent=0, spaceBefore=font_size * 0.6, spaceAfter=font_size * 0.4)
            result.append(Paragraph(inline(block[2]), style))
        elif block[0] == "list":
            style = ParagraphStyle("list", parent=normal, leftIndent=font_size * 1.1, firstLineIndent=-font_size * 0.9, spaceAfter=font_size * 0.3)
            result.append(Paragraph(escape("• " + block[1]), style))
        elif block[0] == "table":
            rows = block[1]
            cell_style = ParagraphStyle("cell", parent=normal, fontSize=font_size * (0.78 if len(rows[0]) >= 5 else 0.86), leading=font_size * 1.12, firstLineIndent=0, spaceAfter=0)
            table = Table([[Paragraph(inline(cell), cell_style) for cell in row] for row in rows], repeatRows=1, colWidths=[width / len(rows[0])] * len(rows[0]))
            table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, LINE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf3f4")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            result.extend([table, Spacer(1, font_size * 0.65)])
        elif block[0] == "visual":
            key = block[2]
            if key not in assets:
                raise ValueError(f"未在 visuals 中声明占位符：{key}")
            result.extend([Visual(assets[key], root, width), Spacer(1, font_size * 0.65)])
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    args = ap.parse_args()
    spec = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.manifest.parent
    source_path = (root / spec["source_pdf"]).resolve()
    output_path = (root / spec["output_pdf"]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source = PdfReader(str(source_path))
    src_w = float(source.pages[0].mediabox.width)
    src_h = float(source.pages[0].mediabox.height)
    if any(float(page.mediabox.width) != src_w or float(page.mediabox.height) != src_h for page in source.pages):
        raise ValueError("来源 PDF 各页尺寸不一致；请先分组处理或明确适配策略。")
    pdfmetrics.registerFont(TTFont("CN", str((root / spec["font_regular"]).resolve())))
    bold_path = (root / spec.get("font_bold", spec["font_regular"])).resolve()
    pdfmetrics.registerFont(TTFont("CNBold", str(bold_path)))
    assets = {item["id"]: item for item in spec.get("visuals", [])}
    by_page = {int(item["page"]): item for item in spec["pages"]}
    if sorted(by_page) != list(range(1, len(source.pages) + 1)):
        raise ValueError("pages 必须覆盖来源 PDF 的全部页，并按 1..N 排列。")

    right_buffer = BytesIO()
    right_canvas = canvas.Canvas(right_buffer, pagesize=(src_w, src_h), pageCompression=1)
    placements = []
    for page_number in range(1, len(source.pages) + 1):
        translation_path = (root / by_page[page_number]["translation"]).resolve()
        blocks = parse_blocks(translation_path.read_text(encoding="utf-8"))
        content_width = src_w - 64
        for step in range(28):
            size = 11.0 - step * 0.1
            flowables = make_flowables(blocks, assets, root, size, content_width)
            heights = []
            total = 0
            for flow in flowables:
                before = getattr(flow, "getSpaceBefore", lambda: 0)()
                after = getattr(flow, "getSpaceAfter", lambda: 0)()
                _, height = flow.wrap(content_width, src_h)
                heights.append((before, height, after))
                total += before + height + after
            if total <= src_h - 78:
                break
        else:
            raise ValueError(f"第 {page_number} 页中文内容溢出，无法在可读字号下排入右栏。")
        right_canvas.setStrokeColor(LINE)
        right_canvas.setLineWidth(0.45)
        right_canvas.line(32, 28, src_w - 32, 28)
        right_canvas.setFont("CN", 7.2)
        right_canvas.setFillColor(MUTED)
        right_canvas.drawString(32, 16, f"中英对照 · 原图形与表格结构保留 · 原页 {page_number}")
        y = src_h - 35
        for flow, (_, height, after) in zip(flowables, heights):
            y -= getattr(flow, "getSpaceBefore", lambda: 0)() + height
            if isinstance(flow, Visual) and flow.kind == "pdf":
                placements.append({"page": page_number, "id": flow.asset_id, "x": (src_w - flow.width) / 2, "y": y, "width": flow.width, "height": flow.height})
            else:
                flow.drawOn(right_canvas, 32, y)
            y -= after
        right_canvas.showPage()
    right_canvas.save()
    right = PdfReader(right_buffer)
    for placement in placements:
        asset = assets[placement["id"]]
        asset_doc = PdfReader(str((root / asset["path"]).resolve()))
        page = right.pages[placement["page"] - 1]
        asset_page = asset_doc.pages[0]
        scale_x = placement["width"] / float(asset_page.mediabox.width)
        scale_y = placement["height"] / float(asset_page.mediabox.height)
        page.merge_transformed_page(asset_page, Transformation().scale(scale_x, scale_y).translate(tx=placement["x"], ty=placement["y"]))

    gutter = 42
    margin = 14
    writer = PdfWriter()
    for number, (left, right_page) in enumerate(zip(source.pages, right.pages), 1):
        spread = PageObject.create_blank_page(width=src_w * 2 + gutter, height=src_h + margin * 2 + 16)
        spread.merge_transformed_page(left, Transformation().translate(tx=margin, ty=margin))
        spread.merge_transformed_page(right_page, Transformation().translate(tx=src_w + gutter - margin, ty=margin))
        writer.add_page(spread)
        writer.add_outline_item(f"第 {number} 页", number - 1)
    writer.add_metadata({"/Title": spec.get("title", "中英对照论文"), "/Author": spec.get("author", ""), "/Subject": "左侧保留原 PDF 文本层与链接；右侧为中文译文"})
    with output_path.open("wb") as stream:
        writer.write(stream)
    print(json.dumps({"output_pdf": str(output_path), "pages": len(writer.pages), "page_width": src_w * 2 + gutter, "page_height": src_h + margin * 2 + 16}, ensure_ascii=False))


if __name__ == "__main__":
    main()
