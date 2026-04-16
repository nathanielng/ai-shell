#!/usr/bin/env python3
"""md2html — Python engine (markdown + pygments)."""

import argparse, pathlib, markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.toc import TocExtension

SCRIPT_DIR = pathlib.Path(__file__).parent
HIGHLIGHT = {"dark": "monokai", "github": "default", "light": "default"}


def convert(md_path, theme="dark", output=None):
    md_text = pathlib.Path(md_path).read_text(encoding="utf-8")
    shared_css = (SCRIPT_DIR / "themes.css").read_text(encoding="utf-8")

    from pygments.formatters import HtmlFormatter
    pygments_css = HtmlFormatter(style=HIGHLIGHT[theme]).get_style_defs('.codehilite')

    md = markdown.Markdown(extensions=[
        "tables", "fenced_code", "footnotes", "attr_list", "def_list",
        CodeHiliteExtension(css_class="codehilite", guess_lang=True, linenums=False),
        TocExtension(marker="[TOC]", toc_depth="2-3"),
    ])
    html_body = md.convert(md_text)

    toc = ""
    if hasattr(md, "toc_tokens") and len(md.toc_tokens) >= 3:
        toc = f'''<button class="toc-toggle" onclick="document.querySelector('.toc-sidebar').classList.toggle('open')" aria-label="Toggle contents">☰</button>
<nav class="toc-sidebar"><strong>Contents</strong>{md.toc}</nav>
<div class="toc-overlay" onclick="document.querySelector('.toc-sidebar').classList.remove('open')"></div>'''

    title = pathlib.Path(md_path).stem.replace("-", " ").replace("_", " ").title()
    out_path = pathlib.Path(output) if output else pathlib.Path(md_path).with_suffix(".html")
    out_path.write_text(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{shared_css}\n{pygments_css}</style>
</head><body class="theme-{theme}">
{toc}{html_body}
<div class="footer">Generated with md2html · python engine · {theme} theme</div>
</body></html>""", encoding="utf-8")
    print(f"✅ {out_path} (python · {theme} · {len(md.toc_tokens)} sections)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="md2html — Python engine")
    p.add_argument("input", help="Markdown file path")
    p.add_argument("--theme", choices=["dark", "github", "light"], default="dark")
    p.add_argument("--output", help="Output HTML path")
    args = p.parse_args()
    convert(args.input, args.theme, args.output)
