# YouTube Transcript Libraries

There are a few good options, and the best one depends on whether the video already has captions/subtitles or not.

---

## Option 1: `youtube-transcript-api` (recommended — no API key needed)

This library fetches transcripts/subtitles for a given YouTube video, works for automatically generated subtitles, and requires neither an API key nor a headless browser.

```bash
uv add youtube-transcript-api
```

The simplest usage — pass in the video ID (not the full URL):

```python
from youtube_transcript_api import YouTubeTranscriptApi
ytt_api = YouTubeTranscriptApi()
transcript = ytt_api.fetch("dQw4w9WgXcQ")  # just the ID, not the full URL
for snippet in transcript:
    print(f"[{snippet.start:.1f}s] {snippet.text}")
```

It returns a `FetchedTranscript` with `text`, `start`, and `duration` per snippet. You can also save to JSON using the built-in `JSONFormatter`. **Caveat:** only works if the video has captions (human or auto-generated). If there are none, it'll raise an exception.

---

## Option 2: `yt-dlp` + Whisper (no API key, but heavier)

Use `yt-dlp` (a well-maintained fork of `youtube-dl`) to download the audio, then transcribe it with OpenAI's Whisper model locally. This approach works even when a video has no captions at all, but requires `ffmpeg` to be installed.

```bash
uv add yt-dlp openai-whisper
brew install ffmpeg  # or apt install ffmpeg
```

This is more involved but useful for videos without subtitles or auto-generated captions. Whisper runs entirely locally — no API key needed.

---

## Option 3: `yt-dlp` + AssemblyAI/cloud STT (API key required)

Same `yt-dlp` download step, but you send the audio to a cloud speech-to-text service like AssemblyAI. This requires an API key but offloads compute. Same pattern works with AWS Transcribe via `boto3`.

---

## Summary

| Option | API Key? | Works without captions? | Notes |
|---|---|---|---|
| `youtube-transcript-api` | No | No | Easiest by far |
| `yt-dlp` + Whisper | No | Yes | Heavy, runs locally |
| `yt-dlp` + cloud STT | Yes | Yes | AWS Transcribe, AssemblyAI, etc. |

For most RAG/AI pipeline use cases, **`youtube-transcript-api`** is the right starting point — fast, zero auth, and the output is already clean timestamped text.
