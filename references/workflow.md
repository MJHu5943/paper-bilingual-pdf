# 中英对照 PDF 工作流

## 依赖

优先使用宿主提供的 Python 运行时。构建脚本需要 `pypdf`、`reportlab` 和 `pypdfium2`；图中文字局部替换额外需要 `PyMuPDF`（导入名可能是 `pymupdf` 或 `fitz`）。字体必须是真实存在且覆盖中文字符的 TTF/OTF 文件。

## 坐标与区域

所有区域用 PDF 点表示，原点在页面左上角：`[x0, y0, x1, y1]`。公式区域应略留边距，避免裁掉编号、根号、上下标或多行对齐。图标签区域只覆盖要替换的字形，不覆盖线条、箭头、背景图片或相邻公式。

## 建议目录

```text
task/
├── source/paper.pdf
├── translation/01.md
├── figures/fig1_zh.pdf
├── formulas/eq1.png
├── manifest.json
└── outputs/paper-bilingual.pdf
```

## Markdown 约定

独立公式、图或表占位符必须独占一个段落：

```text
这是公式前的中文段落。

[[FORMULA:eq1]]

这是公式后的中文段落。
```

表格可以写成标准 Markdown 表格；构建脚本会生成真实 PDF 文字表格。复杂表格或需要完全保留线条的表格，先制作局部 PDF，再使用 `[[TABLE:table1]]`。

## Zotero

只有用户明确要求保存时才写入 Zotero。新增附件用清晰的修订名称，保留旧版及其批注；不要直接覆盖 storage 中的原文件。保存后重新打开附件，抽查文本选择、图和公式。
