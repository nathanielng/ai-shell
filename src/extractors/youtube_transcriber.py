#!/usr/bin/env python3
"""
YouTube Transcript Extractor

Fetches transcripts/subtitles from YouTube videos using youtube-transcript-api.
No API key required. Works with auto-generated and manual captions.

Usage:
    # As a module
    from youtube_transcriber import get_transcript
    transcript = get_transcript("dQw4w9WgXcQ")

    # Direct URL
    python youtube_transcriber.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

    # Video ID
    python youtube_transcriber.py dQw4w9WgXcQ

    # Piped input
    echo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" | python youtube_transcriber.py

    # Save to file
    python youtube_transcriber.py https://www.youtube.com/watch?v=dQw4w9WgXcQ -o transcript.txt
"""

import argparse
import logging
import os
import re
import sys
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

import httpx
from youtube_transcript_api import YouTubeTranscriptApi

# Add lib to path for validation utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from validation import validate_url, validate_output_path

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    parsed = urlparse(url)

    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed.path[1:]

    if parsed.hostname in ('youtube.com', 'www.youtube.com'):
        if parsed.path == '/watch':
            return parse_qs(parsed.query).get('v', [None])[0]
        if parsed.path.startswith(('/embed/', '/v/')):
            return parsed.path.split('/')[2]

    return None


def get_transcript(video_id: str, languages: Optional[List[str]] = None) -> Optional[str]:
    """
    Fetch transcript for a YouTube video.

    Args:
        video_id: YouTube video ID
        languages: Preferred languages in order (default: ['en'])

    Returns:
        Full transcript text, or None if unavailable
    """
    languages = languages or ['en']
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=languages)
        return ' '.join(snippet.text for snippet in transcript)
    except Exception as e:
        logger.warning(f"Could not fetch transcript for {video_id}: {e}")
        return None


def get_title(video_id: str) -> Optional[str]:
    """Fetch video title from YouTube."""
    try:
        resp = httpx.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True, timeout=10
        )
        match = re.search(r"<title>(.+?)</title>", resp.text)
        if match:
            title = match.group(1).removesuffix(" - YouTube").strip()
            return title
    except Exception as e:
        logger.warning(f"Could not fetch title for {video_id}: {e}")
    return None


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text[:max_len].rstrip('-')


def get_author(video_id: str) -> Optional[str]:
    """Fetch video author/channel name from YouTube."""
    try:
        resp = httpx.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True, timeout=10
        )
        match = re.search(r'"author":"([^"]+)"', resp.text)
        if match:
            return match.group(1)
    except Exception as e:
        logger.warning(f"Could not fetch author for {video_id}: {e}")
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract transcript from YouTube video"
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube URL or video ID"
    )
    parser.add_argument(
        "-o", "--output",
        help="Write transcript to file (default: stdout)"
    )
    parser.add_argument(
        "--title", action="store_true",
        help="Print the video title and exit"
    )
    parser.add_argument(
        "--slug", action="store_true",
        help="Print suggested filename slug (slug-videoid) and exit"
    )
    parser.add_argument(
        "--author", action="store_true",
        help="Print the video author/channel name and exit"
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

    # Validate URL format (only http/https allowed)
    try:
        validate_url(input_url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract video ID from URL or use as-is
    vid = extract_video_id(input_url) if '/' in input_url else input_url

    if not vid:
        print(f"Error: Could not extract video ID from: {input_url}", file=sys.stderr)
        sys.exit(1)

    # Handle --title, --slug, and --author flags
    if args.title or args.slug or args.author:
        if args.author:
            author = get_author(vid)
            if not author:
                print(f"Error: Could not fetch author for {vid}", file=sys.stderr)
                sys.exit(1)
            print(author)
        else:
            title = get_title(vid)
            if not title:
                print(f"Error: Could not fetch title for {vid}", file=sys.stderr)
                sys.exit(1)
            if args.slug:
                print(f"{slugify(title)}-{vid}")
            else:
                print(title)
        sys.exit(0)

    # Fetch transcript
    transcript = get_transcript(vid)
    if not transcript:
        print(f"Error: No transcript available for {vid}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        # Validate output path to prevent traversal attacks
        try:
            output_path = validate_output_path(args.output)
        except (ValueError, RuntimeError) as e:
            print(f"Error: Invalid output path: {e}", file=sys.stderr)
            sys.exit(1)

        with open(output_path, "w") as f:
            f.write(transcript)
        print(f"Wrote transcript to {args.output}", file=sys.stderr)
    else:
        print(transcript)
