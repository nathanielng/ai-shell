---
name: md2html
description: Convert markdown files to self-contained, prettified HTML reports with theme options.
metadata:
  tags: markdown, html, report, export, conversion
---

# Markdown to HTML Converter

Convert markdown files to self-contained HTML reports using one of three rendering engines. All CSS is inlined — output is a single `.html` file ready to share or print.

## When to use

- User asks to convert markdown to HTML
- User asks to export a report, summary, or document as HTML
- User asks to "prettify" or "make shareable" a markdown file
- After generating a markdown summary and needing a presentable output

## Engines

Three rendering engines are available. All produce self-contained HTML with the same theme options, sidebar TOC, and print styles.

| Engine | Command | Strengths |
|--------|---------|-----------|
| `python` | `scripts/convert.py` | Tables, TOC, syntax highlighting via Pygments. Best all-rounder. |
| `pandoc` | `scripts/convert-pandoc.sh` | Battle-tested CLI tool. Handles edge cases, footnotes, math. |
| `node` | `scripts/convert.mjs` | Fast, extensible. Good for JS-heavy workflows. |

**Default engine:** `python` (most features, no extra install beyond `pip3 install markdown pygments`).

## Usage

### Python engine (default)

```bash
python3 ~/.kiro/skills/md2html/scripts/convert.py <input.md> [--theme dark|github|light] [--output path.html]
```

### Pandoc engine

```bash
~/.kiro/skills/md2html/scripts/convert-pandoc.sh <input.md> [dark|github|light] [output.html]
```

### Node engine

```bash
node ~/.kiro/skills/md2html/scripts/convert.mjs <input.md> [--theme dark|github|light] [--output path.html]
```

### Parameters (all engines)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input.md` | Yes | — | Path to the markdown file |
| `--theme` / arg 2 | No | `dark` | Theme: `dark`, `github`, or `light` |
| `--output` / arg 3 | No | Same dir as input, `.html` extension | Output file path |

## Themes

All engines share the same 3 themes via `scripts/themes.css`:

| Theme | Best for |
|-------|----------|
| `dark` | Technical reports, internal sharing, presentations |
| `github` | Developer-facing docs, README-style reports |
| `light` | Formal/external sharing, printing |

## Key features

### Collapsible sidebar TOC

When a document has 3 or more headings, a **☰ hamburger button** appears at the top-left. Clicking it slides open a sidebar with the table of contents. Clicking a link jumps to that section; clicking the overlay or button again closes it.

### Print-friendly output

When printing (Cmd+P / Ctrl+P), the output automatically:
- Hides the sidebar TOC, toggle button, and footer
- Forces white background with black text
- Makes table borders visible
- Works regardless of which theme was used on screen

### Shared CSS architecture

All 3 engines read from `scripts/themes.css` at build time and inline it into the HTML. To customize themes, edit `themes.css` — changes apply to all engines on next build.

## Features (by engine)

| Feature | Python | Pandoc | Node |
|---------|--------|--------|------|
| Tables | ✅ | ✅ | ✅ |
| Fenced code blocks | ✅ | ✅ | ✅ |
| Syntax highlighting | ✅ (Pygments) | ✅ (built-in) | ✅ (inline) |
| Sidebar TOC | ✅ (3+ headings) | ✅ (auto) | ✅ (3+ headings) |
| Footnotes | ✅ | ✅ | ✅ |
| Math (LaTeX) | ❌ | ✅ | ❌ |
| Print-friendly | ✅ | ✅ | ✅ |
| Self-contained | ✅ | ✅ | ✅ |
| Responsive | ✅ | ✅ | ✅ |

## File structure

```
~/.kiro/skills/md2html/
├── SKILL.md                        # This file
└── scripts/
    ├── themes.css                  # Shared CSS (3 themes + sidebar + print)
    ├── convert.py                  # Python engine
    ├── convert-pandoc.sh           # Pandoc engine
    ├── convert.mjs                 # Node engine
    ├── package.json                # Node local deps
    └── node_modules/               # markdown-it, markdown-it-footnote
```

## Dependencies

```bash
# Python engine
pip3 install markdown pygments

# Pandoc engine
brew install pandoc

# Node engine (deps are local in scripts/, install once)
cd ~/.kiro/skills/md2html/scripts && npm install
```
