#!/usr/bin/env python3
"""
Web Page to Markdown converter.

Fetches a URL, extracts main content, converts to clean Markdown.

Usage:
    # Direct URL
    python web_to_markdown.py https://example.com/article

    # Piped input
    echo "https://example.com" | python web_to_markdown.py

    # Save to file
    python web_to_markdown.py https://example.com -o article.md

    # As a module
    from web_to_markdown import fetch_and_convert
    markdown = fetch_and_convert("https://example.com")
"""

import sys
import argparse
import os
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Add lib to path for validation utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from validation import validate_url, validate_output_path


def fetch_and_convert(url: str) -> str:
    """Fetch URL or local file and convert to markdown."""
    from pathlib import Path

    # Detect local file: file:// prefix, absolute path, or relative path that exists
    if url.startswith("file://"):
        path = Path(url.removeprefix("file://"))
    elif not url.startswith(("http://", "https://")):
        path = Path(url)
    else:
        path = None

    if path and path.exists():
        raw = path.read_bytes()
        if path.suffix.lower() == ".mhtml" or b"MIME-Version:" in raw[:200]:
            import email
            msg = email.message_from_bytes(raw)
            html = ""
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
            if not html:
                html = raw.decode("utf-8", errors="replace")
        else:
            html = raw.decode("utf-8")
    else:
        # Validate URL before fetching
        validate_url(url)
        resp = httpx.get(url, follow_redirects=True, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        tag.decompose()

    # Try to find main content
    main = soup.find("main") or soup.find("article") or soup.find("div", {"role": "main"})
    content = main if main else soup.body or soup

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    markdown = md(str(content), heading_style="ATX", strip=["img"]).strip()

    if title:
        markdown = f"# {title}\n\n{markdown}"

    return markdown


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert web page to Markdown")
    parser.add_argument(
        "url",
        nargs="?",
        help="URL to convert"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )
    args = parser.parse_args()

    # Read stdin if piped, or use argument
    stdin_text = None
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()

    input_url = args.url or stdin_text

    if not input_url:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    try:
        result = fetch_and_convert(input_url)
    except Exception as e:
        print(f"Error: Failed to convert {input_url}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        # Validate output path to prevent traversal attacks
        try:
            output_path = validate_output_path(args.output)
        except (ValueError, RuntimeError) as e:
            print(f"Error: Invalid output path: {e}", file=sys.stderr)
            sys.exit(1)

        with open(output_path, "w") as f:
            f.write(result)
        print(f"Wrote markdown to {args.output}", file=sys.stderr)
    else:
        print(result)
