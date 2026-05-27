#!/usr/bin/env python3
"""
Audio Transcriber for ai-shell

Transcribe audio files to text on-device using Apple Silicon GPU via Metal.
Supports two backends: mlx-whisper (default) and mlx-audio (Qwen3-ASR).

Usage:
    # Direct file
    python audio_transcriber.py audio.mp3

    # With backend selection
    python audio_transcriber.py audio.mp3 --backend qwen3

    # Piped input (file path)
    echo "audio.mp3" | python audio_transcriber.py

    # Save to file
    python audio_transcriber.py audio.mp3 -o transcript.txt

    # As a module
    from audio_transcriber import transcribe
    transcript = transcribe("audio.mp3")
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add lib to path for validation utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from validation import validate_output_path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')


def check_backend(backend: str = "mlx-whisper") -> bool:
    """Check if the backend package is installed."""
    package_map = {
        "mlx-whisper": "mlx_whisper",
        "qwen3": "mlx_audio",
    }
    package_name = package_map.get(backend, backend)

    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def install_backend(backend: str = "mlx-whisper") -> bool:
    """Attempt to install the backend."""
    import subprocess

    package_map = {
        "mlx-whisper": "mlx-whisper",
        "qwen3": "mlx-audio",
    }
    package = package_map.get(backend)

    if not package:
        logger.error(f"Unknown backend: {backend}")
        return False

    logger.info(f"Installing {package}...")
    try:
        subprocess.run(
            ["uv", "pip", "install", package],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install {package}: {e}")
        return False
    except FileNotFoundError:
        logger.error("uv not found. Please run: uv pip install mlx-whisper")
        return False


def transcribe(
    audio_path: str,
    backend: str = "mlx-whisper",
    language: Optional[str] = None,
    output_dir: Optional[str] = None
) -> str:
    """
    Transcribe an audio file.

    Args:
        audio_path: Path to audio file
        backend: "mlx-whisper" (default) or "qwen3"
        language: Language code (e.g., "en", "zh")
        output_dir: Directory to save transcript (uses AUDIO_TRANSCRIPTIONS_DIR if not set)

    Returns:
        Transcript text

    Raises:
        FileNotFoundError: If audio file doesn't exist
        ImportError: If backend is not installed
        RuntimeError: If transcription fails
    """
    from pathlib import Path

    # Validate audio file
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Check and install backend if needed
    if not check_backend(backend):
        logger.warning(f"{backend} not installed. Attempting to install...")
        if not install_backend(backend):
            raise ImportError(f"Failed to install {backend}")

    # Perform transcription based on backend
    if backend == "mlx-whisper":
        transcript = _transcribe_mlx_whisper(str(audio_file), language)
    elif backend == "qwen3":
        transcript = _transcribe_qwen3(str(audio_file), language)
    else:
        raise ValueError(f"Unknown backend: {backend}")

    # Save to output directory if specified or AUDIO_TRANSCRIPTIONS_DIR is set
    output_dir = output_dir or os.environ.get("AUDIO_TRANSCRIPTIONS_DIR")
    if output_dir:
        output_path = Path(output_dir) / f"{audio_file.stem}-transcript.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(transcript)
        logger.info(f"Saved transcript to: {output_path}")

    return transcript


def _transcribe_mlx_whisper(audio_path: str, language: Optional[str]) -> str:
    """Transcribe using mlx-whisper backend."""
    import mlx_whisper

    logger.info(f"Transcribing with mlx-whisper: {audio_path}")

    kwargs = {
        "path_or_hf_repo": "mlx-community/whisper-large-v3-turbo",
    }
    if language:
        kwargs["language"] = language

    result = mlx_whisper.transcribe(audio_path, **kwargs)
    return result.get("text", "")


def _transcribe_qwen3(audio_path: str, language: Optional[str]) -> str:
    """Transcribe using mlx-audio (Qwen3-ASR) backend."""
    from mlx_audio.stt import load

    logger.info(f"Transcribing with Qwen3-ASR: {audio_path}")

    model = load("mlx-community/Qwen3-ASR-0.6B-8bit")
    language_name = language or "English"
    result = model.generate(audio_path, language=language_name)
    return result.text if hasattr(result, 'text') else str(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe audio to text using Apple Silicon GPU"
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        help="Audio file path (mp3, wav, m4a, flac, ogg, webm)"
    )
    parser.add_argument(
        "--backend",
        choices=["mlx-whisper", "qwen3"],
        default="mlx-whisper",
        help="Transcription backend (default: mlx-whisper)"
    )
    parser.add_argument(
        "--language",
        help="Language code (e.g., en, zh) - optional hint"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file or directory for transcript"
    )

    args = parser.parse_args()

    # Read stdin if piped, or use argument
    stdin_text = None
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()

    input_path = args.audio_file or stdin_text

    if not input_path:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    try:
        # Determine if output is a file or directory
        output_dir = None
        output_file = None

        if args.output:
            output_path = Path(args.output)
            if args.output.endswith('/') or not output_path.suffix:
                # Treat as directory
                output_dir = args.output
            else:
                # Treat as file
                output_file = args.output

        # Transcribe
        transcript = transcribe(
            input_path,
            backend=args.backend,
            language=args.language,
            output_dir=output_dir
        )

        # Write to file if specified
        if output_file:
            try:
                output_path = validate_output_path(output_file)
                with open(output_path, "w") as f:
                    f.write(transcript)
                logger.info(f"Wrote transcript to {output_file}")
            except (ValueError, RuntimeError) as e:
                logger.error(f"Invalid output path: {e}")
                sys.exit(1)
        else:
            # Print to stdout if no file output
            print(transcript)

    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as e:
        logger.error(f"Transcription failed: {e}")
        sys.exit(1)
