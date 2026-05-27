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
import sys
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi

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
    args = parser.parse_args()

    # Read stdin if piped, or use argument
    stdin_text = None
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()

    input_url = args.url or stdin_text

    if not input_url:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    # Extract video ID from URL or use as-is
    vid = extract_video_id(input_url) if '/' in input_url else input_url

    if not vid:
        print(f"Error: Could not extract video ID from: {input_url}", file=sys.stderr)
        sys.exit(1)

    # Fetch transcript
    transcript = get_transcript(vid)
    if not transcript:
        print(f"Error: No transcript available for {vid}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(transcript)
        print(f"Wrote transcript to {args.output}", file=sys.stderr)
    else:
        print(transcript)
