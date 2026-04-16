#!/usr/bin/env node
// md2html — Node engine (markdown-it + markdown-it-footnote)

import { readFileSync, writeFileSync } from 'fs';
import { basename, dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';
import markdownIt from 'markdown-it';
import footnote from 'markdown-it-footnote';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Parse args
const args = process.argv.slice(2);
let input, theme = 'dark', output;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--theme') theme = args[++i];
  else if (args[i] === '--output') output = args[++i];
  else if (!input) input = args[i];
}
if (!input) { console.error('Usage: convert.mjs <input.md> [--theme dark|github|light] [--output path.html]'); process.exit(1); }

const mdText = readFileSync(resolve(input), 'utf-8');
const sharedCss = readFileSync(join(__dirname, 'themes.css'), 'utf-8');

// Count headings for TOC decision
const headings = [];
const md = markdownIt({ html: true, linkify: true, typographer: true }).use(footnote);

// Collect headings via ruler
md.core.ruler.push('collect_headings', (state) => {
  for (const token of state.tokens) {
    if (token.type === 'heading_open') {
      const level = parseInt(token.tag.slice(1));
      const inline = state.tokens[state.tokens.indexOf(token) + 1];
      const text = inline?.children?.map(t => t.content).join('') || '';
      const id = text.toLowerCase().replace(/[^\w]+/g, '-').replace(/(^-|-$)/g, '');
      token.attrSet('id', id);
      if (level >= 2 && level <= 3) headings.push({ level, text, id });
    }
  }
});

const htmlBody = md.render(mdText);

// Build TOC if 3+ headings
let toc = '';
if (headings.length >= 3) {
  const items = headings.map(h =>
    `<li style="padding-left:${(h.level - 2) * 0.8}rem"><a href="#${h.id}">${h.text}</a></li>`
  ).join('\n');
  toc = `<button class="toc-toggle" onclick="document.querySelector('.toc-sidebar').classList.toggle('open')" aria-label="Toggle contents">☰</button>
<nav class="toc-sidebar"><strong>Contents</strong><ul>${items}</ul></nav>
<div class="toc-overlay" onclick="document.querySelector('.toc-sidebar').classList.remove('open')"></div>`;
}

const title = basename(input, '.md').replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const outPath = output || input.replace(/\.md$/, '.html');

const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title>
<style>${sharedCss}</style>
</head><body class="theme-${theme}">
${toc}${htmlBody}
<div class="footer">Generated with md2html · node engine · ${theme} theme</div>
</body></html>`;

writeFileSync(resolve(outPath), html, 'utf-8');
console.log(`✅ ${outPath} (node · ${theme} · ${headings.length} sections)`);
