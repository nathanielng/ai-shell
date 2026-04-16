#!/usr/bin/env bash
# md2html — Pandoc engine
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="${1:?Usage: convert-pandoc.sh <input.md> [dark|github|light] [output.html]}"
THEME="${2:-dark}"
OUTPUT="${3:-${INPUT%.md}.html}"

CSS=$(cat "$SCRIPT_DIR/themes.css")
TITLE=$(basename "${INPUT%.md}" | sed 's/[-_]/ /g')

HIGHLIGHT="pygments"
[ "$THEME" = "dark" ] && HIGHLIGHT="breezedark"

# Generate body with TOC
BODY=$(pandoc "$INPUT" \
  --from markdown+footnotes+pipe_tables+fenced_code_blocks \
  --to html5 \
  --highlight-style="$HIGHLIGHT" \
  --toc --toc-depth=3 2>/dev/null || pandoc "$INPUT" --to html5)

# Extract pandoc's TOC (it's the first <nav> with id="TOC") and wrap in sidebar
TOC_NAV=""
if echo "$BODY" | grep -q 'id="TOC"'; then
  TOC_CONTENT=$(echo "$BODY" | sed -n '/<nav id="TOC"/,/<\/nav>/p')
  BODY=$(echo "$BODY" | sed '/<nav id="TOC"/,/<\/nav>/d')
  # Rewrite into sidebar markup
  TOC_INNER=$(echo "$TOC_CONTENT" | sed 's/<nav[^>]*>//' | sed 's/<\/nav>//')
  TOC_NAV="<button class=\"toc-toggle\" onclick=\"document.querySelector('.toc-sidebar').classList.toggle('open')\" aria-label=\"Toggle contents\">☰</button>
<nav class=\"toc-sidebar\"><strong>Contents</strong>${TOC_INNER}</nav>
<div class=\"toc-overlay\" onclick=\"document.querySelector('.toc-sidebar').classList.remove('open')\"></div>"
fi

cat > "$OUTPUT" <<EOF
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>$TITLE</title>
<style>$CSS</style>
</head><body class="theme-$THEME">
$TOC_NAV
$BODY
<div class="footer">Generated with md2html · pandoc engine · $THEME theme</div>
</body></html>
EOF

echo "✅ $OUTPUT (pandoc · $THEME)"
