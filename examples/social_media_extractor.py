#!/usr/bin/env python3
"""
Social Media Content Extractor

Extracts metadata and content from URLs across multiple platforms.
Supports single URL extraction or CSV batch processing.

Usage:
    # Single URL (outputs JSON)
    python social_media_extractor.py https://linkedin.com/posts/...

    # Piped URL
    echo "https://linkedin.com/posts/..." | python social_media_extractor.py

    # CSV input from stdin (outputs JSONL)
    cat urls.csv | python social_media_extractor.py --csv

    # CSV input from file (outputs JSONL)
    python social_media_extractor.py --csv urls.csv

    # Output to file
    python social_media_extractor.py --csv urls.csv -o results.jsonl

Supported Platforms:
    - LinkedIn: Posts and articles
    - X/Twitter: Tweets and posts
    - Instagram: Posts and reels
    - YouTube: Videos and community posts
    - AWS Blogs: Blog posts
    - GitHub: Repositories, issues, PRs, GitHub Pages

Environment Variables:
    YOUTUBE_API_KEY: Optional YouTube Data API key for enhanced metadata
    TWITTER_BEARER_TOKEN: Optional X/Twitter API bearer token
    SAVE_RAW_HTML: Set to 'true' to include raw HTML in results
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add src/extractors to path so we can import youtube_transcriber
extractors_path = Path(__file__).parent.parent / 'src' / 'extractors'
if str(extractors_path) not in sys.path:
    sys.path.insert(0, str(extractors_path))

from youtube_transcriber import get_transcript

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class SocialMediaExtractor:
    """Extracts content from various social media platforms."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')

    def get_platform(self, url: str) -> str:
        """Identify the platform from a URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')

        if 'linkedin.com' in domain:
            return 'linkedin'
        elif 'x.com' in domain or 'twitter.com' in domain:
            return 'x'
        elif 'instagram.com' in domain:
            return 'instagram'
        elif 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        elif 'aws.amazon.com' in domain and '/blogs/' in url:
            return 'aws'
        elif 'github.com' in domain or 'github.io' in domain:
            return 'github'
        else:
            return 'unknown'

    def extract(self, url: str) -> Dict[str, Any]:
        """Extract content from a social media URL."""
        logger.info(f"Processing URL: {url}")

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')

        try:
            if 'linkedin.com' in domain:
                return self._extract_linkedin(url)
            elif 'x.com' in domain or 'twitter.com' in domain:
                return self._extract_x(url)
            elif 'instagram.com' in domain:
                return self._extract_instagram(url)
            elif 'youtube.com' in domain or 'youtu.be' in domain:
                return self._extract_youtube(url)
            elif 'aws.amazon.com' in domain and '/blogs/' in url:
                return self._extract_aws(url)
            elif 'github.com' in domain or 'github.io' in domain:
                return self._extract_github(url)
            else:
                logger.warning(f"Unsupported platform: {domain}")
                return {
                    'platform': 'unknown',
                    'url': url,
                    'error': 'Unsupported platform'
                }
        except Exception as e:
            logger.error(f"Error extracting from {url}: {e}", exc_info=True)
            return {
                'platform': domain,
                'url': url,
                'error': str(e)
            }

    def _extract_linkedin(self, url: str) -> Dict[str, Any]:
        """Extract content from LinkedIn post."""
        logger.info("Extracting LinkedIn content")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        content = None
        author = None

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')

        if og_title:
            title = og_title.get('content', '').strip()

        if og_description:
            content = og_description.get('content', '').strip()

        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            author = author_meta.get('content', '').strip()

        if not content:
            post_content = soup.find('div', class_=re.compile(r'feed-shared-update-v2__description'))
            if post_content:
                content = post_content.get_text(strip=True, separator='\n')

        return {
            'platform': 'linkedin',
            'url': url,
            'title': title or 'LinkedIn Post',
            'content': content,
            'author': author,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None
        }

    def _extract_x(self, url: str) -> Dict[str, Any]:
        """Extract content from X (Twitter) post."""
        logger.info("Extracting X (Twitter) content")

        if self.twitter_bearer_token:
            try:
                return self._extract_x_api(url)
            except Exception as e:
                logger.warning(f"X API extraction failed, falling back to scraping: {e}")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        content = None
        author = None

        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        twitter_description = soup.find('meta', attrs={'name': 'twitter:description'})
        twitter_creator = soup.find('meta', attrs={'name': 'twitter:creator'})

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')

        meta_description = soup.find('meta', attrs={'name': 'description'})

        if twitter_title:
            title = twitter_title.get('content', '').strip()
        elif og_title:
            title = og_title.get('content', '').strip()

        if twitter_description:
            content = twitter_description.get('content', '').strip()
        elif og_description:
            content = og_description.get('content', '').strip()
        elif meta_description:
            content = meta_description.get('content', '').strip()

        if twitter_creator:
            author = twitter_creator.get('content', '').strip().lstrip('@')
        elif title:
            if ' on X:' in title:
                author = title.split(' on X:')[0].strip()
            elif ':' in title and len(title.split(':')[0]) < 50:
                potential_author = title.split(':')[0].strip()
                if len(potential_author) < 30 and not any(c in potential_author for c in ['(', ')', '[', ']']):
                    author = potential_author

        if not author and '/status/' in url:
            parts = url.split('/')
            try:
                username_idx = parts.index('x.com') + 1
                if username_idx < len(parts) and parts[username_idx + 1] == 'status':
                    author = parts[username_idx]
            except (ValueError, IndexError):
                pass

        if not content and title and len(title) > 30:
            if ' on X:' in title:
                content = title.split(' on X:')[1].strip()
            elif author and title.startswith(author):
                content = title[len(author):].lstrip(':').strip()

        return {
            'platform': 'x',
            'url': url,
            'title': title or 'X Post',
            'content': content or 'Content unavailable (login required)',
            'author': author,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None
        }

    def _extract_x_api(self, url: str) -> Dict[str, Any]:
        """Extract content from X (Twitter) post using API."""
        logger.info("Using X API for tweet extraction")

        tweet_id = None
        if '/status/' in url:
            parts = url.split('/status/')
            if len(parts) > 1:
                tweet_id = parts[1].split('?')[0].split('/')[0]

        if not tweet_id:
            raise ValueError("Could not extract tweet ID from URL")

        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        params = {
            'tweet.fields': 'author_id,created_at,text,public_metrics',
            'expansions': 'author_id',
            'user.fields': 'username,name'
        }

        headers = {
            'Authorization': f'Bearer {self.twitter_bearer_token}'
        }

        response = self.session.get(api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if 'data' not in data:
            raise ValueError("Tweet not found")

        tweet = data['data']
        author_info = data.get('includes', {}).get('users', [{}])[0]

        return {
            'platform': 'x',
            'url': url,
            'tweet_id': tweet_id,
            'title': f"{author_info.get('name', 'User')} on X",
            'content': tweet.get('text', ''),
            'author': author_info.get('username', ''),
            'author_name': author_info.get('name', ''),
            'created_at': tweet.get('created_at', ''),
            'metrics': tweet.get('public_metrics', {}),
            'raw_html': None
        }

    def _extract_instagram(self, url: str) -> Dict[str, Any]:
        """Extract content from Instagram post."""
        logger.info("Extracting Instagram content")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        content = None
        author = None

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')

        if og_title:
            title = og_title.get('content', '').strip()

        if og_description:
            content = og_description.get('content', '').strip()

        if title and ' on Instagram:' in title:
            author = title.split(' on Instagram:')[0].strip()

        return {
            'platform': 'instagram',
            'url': url,
            'title': title or 'Instagram Post',
            'content': content,
            'author': author,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None
        }

    def _extract_youtube(self, url: str) -> Dict[str, Any]:
        """Extract content from YouTube post or video."""
        logger.info("Extracting YouTube content")

        is_community_post = '/post/' in url

        if is_community_post:
            return self._extract_youtube_post(url)
        else:
            return self._extract_youtube_video(url)

    def _extract_youtube_post(self, url: str) -> Dict[str, Any]:
        """Extract content from YouTube community post."""
        logger.info("Extracting YouTube community post")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        content = None
        author = None

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')

        if og_title:
            title = og_title.get('content', '').strip()

        if og_description:
            content = og_description.get('content', '').strip()

        author_meta = soup.find('link', attrs={'itemprop': 'name'})
        if author_meta:
            author = author_meta.get('content', '').strip()

        return {
            'platform': 'youtube',
            'content_type': 'community_post',
            'url': url,
            'title': title or 'YouTube Community Post',
            'content': content,
            'author': author,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None
        }

    def _extract_youtube_video(self, url: str) -> Dict[str, Any]:
        """Extract content and transcript from YouTube video using parallel fetching."""
        logger.info("Extracting YouTube video (metadata + transcript in parallel)")

        video_id = self._extract_youtube_video_id(url)
        if not video_id:
            raise ValueError("Could not extract YouTube video ID")

        def fetch_metadata():
            if self.youtube_api_key:
                return self._extract_youtube_video_api(video_id)
            return self._scrape_youtube_metadata(video_id)

        def fetch_transcript():
            return get_transcript(video_id)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self._parallel_youtube_fetch(fetch_metadata, fetch_transcript)
            )
        finally:
            loop.close()

        return result

    async def _parallel_youtube_fetch(self, metadata_fn, transcript_fn) -> Dict[str, Any]:
        """Run metadata and transcript fetching in parallel threads."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as pool:
            metadata_task = loop.run_in_executor(pool, metadata_fn)
            transcript_task = loop.run_in_executor(pool, transcript_fn)
            metadata, transcript = await asyncio.gather(metadata_task, transcript_task)

        metadata['transcript'] = transcript
        return metadata

    def _scrape_youtube_metadata(self, video_id: str) -> Dict[str, Any]:
        """Scrape YouTube video metadata via HTML meta tags."""
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        response = self.session.get(watch_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')
        author_meta = soup.find('link', attrs={'itemprop': 'name'})

        return {
            'platform': 'youtube',
            'content_type': 'video',
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'video_id': video_id,
            'title': (og_title.get('content', '').strip() if og_title else None) or 'YouTube Video',
            'content': og_description.get('content', '').strip() if og_description else None,
            'author': author_meta.get('content', '').strip() if author_meta else None,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None,
        }

    def _extract_youtube_video_api(self, video_id: str) -> Dict[str, Any]:
        """Extract YouTube video data using API."""
        logger.info(f"Using YouTube API for video {video_id}")

        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': video_id,
            'key': self.youtube_api_key
        }

        response = self.session.get(api_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data.get('items'):
            raise ValueError("Video not found")

        item = data['items'][0]
        snippet = item['snippet']

        return {
            'platform': 'youtube',
            'content_type': 'video',
            'video_id': video_id,
            'title': snippet['title'],
            'content': snippet['description'],
            'author': snippet['channelTitle'],
            'published_at': snippet['publishedAt'],
            'tags': snippet.get('tags', []),
            'category_id': snippet['categoryId'],
            'statistics': item.get('statistics', {}),
            'url': f"https://www.youtube.com/watch?v={video_id}"
        }

    @staticmethod
    def _extract_youtube_video_id(url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        parsed = urlparse(url)

        if parsed.hostname in ('youtu.be', 'www.youtu.be'):
            return parsed.path[1:]

        if parsed.hostname in ('youtube.com', 'www.youtube.com'):
            if parsed.path == '/watch':
                query = parse_qs(parsed.query)
                return query.get('v', [None])[0]
            elif parsed.path.startswith('/embed/'):
                return parsed.path.split('/')[2]
            elif parsed.path.startswith('/v/'):
                return parsed.path.split('/')[2]

        return None

    def _extract_aws(self, url: str) -> Dict[str, Any]:
        """Extract content from AWS blog post."""
        logger.info("Extracting AWS blog content")

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        content = None
        author = None
        published_date = None

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')
        meta_description = soup.find('meta', attrs={'name': 'description'})

        if og_title:
            title = og_title.get('content', '').strip()

        if og_description:
            content = og_description.get('content', '').strip()
        elif meta_description:
            content = meta_description.get('content', '').strip()

        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)

        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            author = author_meta.get('content', '').strip()
        else:
            author_elem = soup.find('a', class_=re.compile(r'author'))
            if not author_elem:
                author_elem = soup.find('span', class_=re.compile(r'author'))
            if author_elem:
                author = author_elem.get_text(strip=True)

        date_meta = soup.find('meta', property='article:published_time')
        if not date_meta:
            date_meta = soup.find('meta', attrs={'name': 'publish-date'})
        if date_meta:
            published_date = date_meta.get('content', '').strip()
        else:
            date_elem = soup.find('time')
            if date_elem:
                published_date = date_elem.get('datetime', '') or date_elem.get_text(strip=True)

        blog_category = None
        if '/blogs/' in url:
            parts = url.split('/blogs/')
            if len(parts) > 1:
                category_part = parts[1].split('/')[0]
                blog_category = category_part

        return {
            'platform': 'aws',
            'url': url,
            'title': title or 'AWS Blog Post',
            'content': content,
            'author': author,
            'published_date': published_date,
            'blog_category': blog_category,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None
        }

    def _extract_github(self, url: str) -> Dict[str, Any]:
        """Extract content from GitHub (repositories, issues, PRs, GitHub Pages)."""
        logger.info("Extracting GitHub content")

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        is_github_pages = 'github.io' in domain
        content_type = 'github_pages' if is_github_pages else 'github'

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        content = None
        author = None
        repo_info = None

        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')
        meta_description = soup.find('meta', attrs={'name': 'description'})

        if og_title:
            title = og_title.get('content', '').strip()

        if og_description:
            content = og_description.get('content', '').strip()
        elif meta_description:
            content = meta_description.get('content', '').strip()

        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)

        if not is_github_pages and 'github.com' in domain:
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo_name = path_parts[1]
                repo_info = f"{owner}/{repo_name}"
                author = owner

                if len(path_parts) > 2:
                    if path_parts[2] == 'issues':
                        content_type = 'github_issue'
                    elif path_parts[2] == 'pull':
                        content_type = 'github_pr'
                    elif path_parts[2] == 'discussions':
                        content_type = 'github_discussion'
                else:
                    content_type = 'github_repo'

        if is_github_pages:
            subdomain = domain.split('.github.io')[0]
            if subdomain:
                author = subdomain

        if not content:
            readme = soup.find('article', class_=re.compile(r'markdown'))
            if readme:
                first_p = readme.find('p')
                if first_p:
                    content = first_p.get_text(strip=True)[:500]

        return {
            'platform': 'github',
            'content_type': content_type,
            'url': url,
            'title': title or 'GitHub Content',
            'content': content,
            'author': author,
            'repo_info': repo_info,
            'raw_html': str(soup) if os.getenv('SAVE_RAW_HTML') == 'true' else None
        }


def extract(url: str) -> Dict[str, Any]:
    """Module-level API: extract metadata from a URL."""
    extractor = SocialMediaExtractor()
    return extractor.extract(url)


def process_csv(csv_file) -> None:
    """Read CSV from file or stdin, output JSONL to stdout."""
    extractor = SocialMediaExtractor()
    reader = csv.DictReader(csv_file)

    for row in reader:
        url = row.get('url', '').strip()
        if not url:
            continue

        try:
            result = extractor.extract(url)
            print(json.dumps(result))
        except Exception as e:
            logger.error(f"Error processing {url}: {e}", exc_info=True)
            print(json.dumps({
                'url': url,
                'error': str(e)
            }))


def main():
    parser = argparse.ArgumentParser(
        description='Extract metadata from social media URLs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single URL
  python social_media_extractor.py https://linkedin.com/posts/...

  # Piped URL
  echo "https://linkedin.com/posts/..." | python social_media_extractor.py

  # CSV from file
  python social_media_extractor.py --csv urls.csv

  # CSV from stdin
  cat urls.csv | python social_media_extractor.py --csv

  # Output to file
  python social_media_extractor.py --csv urls.csv -o results.jsonl
        """
    )

    parser.add_argument('url', nargs='?', help='URL to extract (or read from stdin)')
    parser.add_argument('--csv', action='store_true', help='Process CSV input (from stdin or file argument)')
    parser.add_argument('-o', '--output', help='Write output to file (default: stdout)')
    args = parser.parse_args()

    # Read stdin if piped
    stdin_text = None
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()

    # CSV mode
    if args.csv:
        if args.url:
            # CSV from file
            try:
                with open(args.url, 'r', encoding='utf-8') as f:
                    csv_file = f
                    if args.output:
                        with open(args.output, 'w') as outf:
                            old_stdout = sys.stdout
                            sys.stdout = outf
                            process_csv(csv_file)
                            sys.stdout = old_stdout
                    else:
                        process_csv(csv_file)
            except FileNotFoundError:
                print(f"Error: CSV file not found: {args.url}", file=sys.stderr)
                sys.exit(1)
        elif stdin_text:
            # CSV from stdin
            from io import StringIO
            csv_file = StringIO(stdin_text)
            if args.output:
                with open(args.output, 'w') as outf:
                    old_stdout = sys.stdout
                    sys.stdout = outf
                    process_csv(csv_file)
                    sys.stdout = old_stdout
            else:
                process_csv(csv_file)
        else:
            parser.error('CSV mode requires either a filename or piped input')
        return

    # Single URL mode
    url = args.url or stdin_text
    if not url:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    try:
        result = extract(url)
        output = json.dumps(result, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Written to {args.output}", file=sys.stderr)
        else:
            print(output)
    except Exception as e:
        logger.error(f"Failed to extract from {url}: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
