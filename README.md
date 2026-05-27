# ai-shell

A collection of composable CLI tools for extracting, processing, and analyzing content from social media and YouTube — powered by AI via AWS Bedrock.

Built on Unix philosophy: small, focused tools that do one thing well and work together seamlessly.

## Quick Start

### Extract & Summarize

```bash
python src/extractors/youtube_transcriber.py https://youtube.com/watch?v=... \
  | python src/agents/strands_cli.py "Summarize this into key points" \
  > summary.txt
```

### Extract Social Media Metadata

```bash
# Single URL
python src/extractors/social_media_extractor.py https://linkedin.com/posts/...

# Batch from CSV
cat urls.csv | python src/extractors/social_media_extractor.py
```

### Convert Web Page to Markdown

```bash
python src/extractors/web_to_markdown.py https://example.com/article
```

### Transcribe Audio

```bash
# Default (mlx-whisper)
python src/extractors/audio_transcriber.py recording.mp3

# Qwen3-ASR for CJK languages
python src/extractors/audio_transcriber.py recording.mp3 --backend qwen3

# Transcribe and summarize
python src/extractors/audio_transcriber.py recording.mp3 \
  | python src/agents/strands_cli.py "Summarize the key points"
```

See `~/code/ai-skills/audio-transcribe/SKILL.md` for full documentation and backend comparison.

## Tools

### Extractors (`src/extractors/`)

- **`audio_transcriber.py`** — Transcribe audio to text on-device using Apple Silicon GPU (mlx-whisper or Qwen3-ASR)
- **`youtube_transcriber.py`** — Fetch YouTube transcripts/subtitles (no API key required)
- **`social_media_extractor.py`** — Extract metadata from LinkedIn, X, Instagram, YouTube, AWS blogs, GitHub
- **`web_to_markdown.py`** — Convert web pages to clean Markdown

### Agents (`src/agents/`)

- **`strands_cli.py`** — AI reasoning agent (Claude via AWS Bedrock). Reads stdin or prompt args, outputs to stdout or file.

### Monitors (`src/monitors/`)

- **`clipboard_url_monitor.py`** — Monitor clipboard for URLs, save to CSV with timestamps

## Design Philosophy

See [DESIGN.md](DESIGN.md) for complete design principles, best practices, and guidelines for extending the project.

Core principles:
- **Do one thing and do it well** — each tool has a single, clear responsibility
- **Composable** — tools work together through pipes and redirection
- **Plain text interfaces** — universal input/output format
- **No hidden behavior** — tools don't change output based on context

## Setup

### Prerequisites

- Python 3.10+
- AWS account with Bedrock access (for `strands_cli.py` only)

### Install Dependencies

```bash
cd src && pip install -r requirements.txt
```

Or with uv (recommended):

```bash
uv pip install -r src/requirements.txt
```

### Configure Environment

Copy `.env.example` and customize:

```bash
cp .env.example .env
# Edit .env with your API keys and preferences
```

See [`.env.example`](.env.example) for all available variables:
- `AWS_BEARER_TOKEN_BEDROCK` — Bedrock API credentials (required for agents)
- `BEDROCK_REGION` — AWS region (default: us-west-2)
- `AISH_MODEL_ID`, `AISH_TEMPERATURE`, `AISH_MAX_TOKENS` — Agent defaults
- `YOUTUBE_API_KEY` — YouTube API (optional; enhanced metadata)
- `TWITTER_BEARER_TOKEN` — X/Twitter API (optional; full tweet access)
- `LOG_LEVEL` — Debug logging (default: WARNING)

**Note:** `.env` is gitignored and never committed. Keep credentials secure.

## Examples

### Pipeline: Extract, Summarize, Tweet

```bash
python src/extractors/youtube_transcriber.py https://youtube.com/watch?v=... \
  | python src/agents/strands_cli.py "Extract 3 key points" \
  | python src/agents/strands_cli.py -s "You are a Twitter writer" "Turn into a tweet (280 chars max)" \
  > tweet.txt
```

### Pipeline: Extract Multiple, Filter, Count

```bash
cat urls.csv \
  | python src/extractors/social_media_extractor.py \
  | grep -E "platform.*linkedin" \
  | wc -l
```

### JSON Output (for Programmatic Use)

```bash
# JSONL (one JSON object per line)
python src/extractors/social_media_extractor.py --json urls.csv | jq '.author'

# Process with jq
python src/extractors/social_media_extractor.py --json urls.csv \
  | jq 'select(.platform == "twitter")'
```

## Project Structure

```
ai-shell/
├── DESIGN.md                    # Design principles & best practices
├── README.md                    # This file
├── .env                         # Credentials (gitignored)
├── src/
│   ├── extractors/              # Data extraction tools
│   │   ├── audio_transcriber.py
│   │   ├── youtube_transcriber.py
│   │   ├── social_media_extractor.py
│   │   └── web_to_markdown.py
│   ├── agents/                  # AI reasoning agents
│   │   └── strands_cli.py
│   ├── monitors/                # Long-running monitors
│   │   └── clipboard_url_monitor.py
│   └── requirements.txt
├── lib/                         # Shared utilities (future)
├── examples/                    # Reference scripts & tools
│   ├── aish.py
│   ├── find_duplicates.py
│   └── upload_layer.py
└── output/                      # Generated files (gitignored)
```

## Contributing

Before adding a new tool, read [DESIGN.md](DESIGN.md) — especially:
- [Extending the Project](DESIGN.md#extending-the-project)
- [Checklist for New Tools](DESIGN.md#checklist-for-new-tools)
- [The Option Creep Problem](DESIGN.md#the-option-creep-problem-crucial)
