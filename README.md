# Paper Bilingual PDF

一个用于 Codex 的论文中英对照 PDF skill：将论文原页放在左侧，同页中文译文放在右侧，便于逐页阅读和核对。

## 功能

- 直接合并英文原始 PDF 页面，保留原有文字和矢量内容，并检查链接与跳转。
- 以可选择、可复制的文字排版中文标题、正文、图注、表格和参考文献。
- 按人工确认的坐标裁取复杂公式；图表保留原有结构，仅局部替换经核对的文字标签。
- 提供 PDF 检查、图表标签处理、页面组装和结构验收脚本，以及参考版式。

翻译、图表区域和最终阅读效果仍需要人工核对。脚本无法保证所有 PDF 的链接、目录或复杂版式自动完整保留；必须按 `SKILL.md` 的验收要求检查，未通过时不要视为完成。

## 安装

将本仓库的文件复制到 Codex 的 skill 目录，例如：

```bash
mkdir -p ~/.codex/skills/paper-bilingual-pdf
cp -R . ~/.codex/skills/paper-bilingual-pdf/
```

在仓库根目录执行上述命令，或直接将仓库克隆到该目录。安装后，在 Codex 中调用 `$paper-bilingual-pdf`，并提供论文 PDF 或指定 Zotero 中的附件。按需重新打开 Codex 以加载新 skill。

## 环境

需要 Python、覆盖中文的可嵌入字体，以及以下依赖：

```bash
python -m pip install pypdf reportlab pypdfium2 Pillow PyMuPDF
```

`PyMuPDF` 用于图中文字的局部替换；请在任务环境中安装依赖，不要将依赖目录放入 skill。生成的论文与中间文件应放在独立任务目录中。

## 使用流程

1. 确认论文版本、页数、页面尺寸、文字层和链接；使用 `scripts/inspect_pdf.py` 生成检查清单。
2. 建立术语表和逐页中文 Markdown 译文，人工确认公式和图表区域。
3. 按需使用 `scripts/extract_formula_images.py` 和 `scripts/localize_figure_labels.py` 处理公式和图表。
4. 编写清单并运行 `scripts/build_bilingual_pdf.py` 组装 PDF。
5. 使用 `scripts/check_bilingual_pdf.py` 检查结构，并在 PDF 阅读器中抽查文本选择、链接、图表、公式和版面。

```bash
python scripts/inspect_pdf.py task/source/paper.pdf --out task/inspection.json
python scripts/build_bilingual_pdf.py task/manifest.json
python scripts/check_bilingual_pdf.py task/source/paper.pdf task/outputs/paper-bilingual.pdf --out task/check.json
```

完整清单示例、占位符和操作要求见 [SKILL.md](SKILL.md) 与 [工作流说明](references/workflow.md)。脚本的详细参数可通过 `python scripts/<脚本名> --help` 查看。

## 文件结构

```text
├── SKILL.md                     # skill 指令与验收要求
├── agents/openai.yaml           # Codex 展示配置
├── scripts/                     # 检查、裁图、标签处理、组装与验收脚本
└── references/                  # 工作流和参考版式说明
```

参考 PDF 包含第三方论文，公开版本不附带该文件；版式参数仍保留在参考说明中。`SKILL.md` 中关于 Zotero 保存的相邻 HTML skill 链接仅在同时安装 `paper-bilingual-html` 时可用；不影响本 skill 的基本 PDF 工作流。只有用户明确要求时才将结果保存到 Zotero，且应保留原附件与批注。
