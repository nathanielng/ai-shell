#!/usr/bin/env python3
"""
Input validation utilities for security.

Provides sanitization for:
- File paths (path traversal prevention)
- URLs (scheme validation)
- Model IDs (format validation)
"""

import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Union


def validate_output_path(filepath: str, allow_dir: str = ".") -> Path:
    """
    Validate output file path to prevent traversal attacks.

    Ensures the resolved path stays within allow_dir (default: current directory).
    Uses pathlib.resolve() to canonicalize and follow symlinks, then validates
    the final path stays within boundaries.

    Args:
        filepath: User-provided output file path
        allow_dir: Base directory to restrict output (default: current directory)

    Returns:
        Validated Path object (canonicalized)

    Raises:
        ValueError: If path is outside allow_dir or invalid
        RuntimeError: If path resolution fails (e.g., permission denied)

    Examples:
        >>> validate_output_path("output.txt")
        PosixPath('/Users/nat/code/ai-shell/output.txt')

        >>> validate_output_path("../../../etc/passwd")
        ValueError: Invalid output path '../../../etc/passwd': ...
    """
    try:
        resolved = Path(filepath).resolve()
        allowed = Path(allow_dir).resolve()

        # Ensure resolved path is within allowed directory
        # This raises ValueError if path is outside allowed directory
        resolved.relative_to(allowed)

        return resolved
    except ValueError as e:
        raise ValueError(
            f"Invalid output path '{filepath}': "
            f"path must be within {allow_dir}"
        ) from e
    except RuntimeError as e:
        raise RuntimeError(f"Cannot resolve path '{filepath}': {e}") from e


def validate_url(url: str, allowed_schemes: list = None) -> str:
    """
    Validate URL format and scheme.

    Only allows http/https by default to prevent:
    - file:// URLs (local file access)
    - ftp://, gopher://, etc. (unexpected protocols)
    - Malformed URLs without proper domain

    Args:
        url: URL to validate
        allowed_schemes: List of allowed schemes (default: ['http', 'https'])

    Returns:
        Validated URL string (unchanged if valid)

    Raises:
        ValueError: If URL scheme is not allowed or URL is malformed

    Examples:
        >>> validate_url("https://example.com/page")
        'https://example.com/page'

        >>> validate_url("file:///etc/passwd")
        ValueError: Invalid URL scheme 'file'. Only http, https allowed.

        >>> validate_url("https://")
        ValueError: Invalid URL 'https://': missing domain
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Malformed URL '{url}': {e}") from e

    # Check scheme
    if not parsed.scheme:
        raise ValueError(f"Invalid URL '{url}': missing scheme (http or https)")

    if parsed.scheme not in allowed_schemes:
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}'. "
            f"Only {', '.join(allowed_schemes)} allowed."
        )

    # Check netloc (domain)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL '{url}': missing domain")

    return url


def validate_model_id(model_id: str) -> str:
    """
    Validate Bedrock model ID format.

    Ensures model ID matches expected format:
    - us.anthropic.claude-* (Anthropic models via Bedrock)
    - us.amazon.nova-* (Amazon Nova models)
    - Other valid Bedrock format: {region}.{provider}.{model}

    Args:
        model_id: Model ID string to validate

    Returns:
        Validated model_id (unchanged if valid)

    Raises:
        ValueError: If model ID format is invalid

    Examples:
        >>> validate_model_id("us.anthropic.claude-sonnet-4-6")
        'us.anthropic.claude-sonnet-4-6'

        >>> validate_model_id("us.amazon.nova-lite-v1:0")
        'us.amazon.nova-lite-v1:0'

        >>> validate_model_id("invalid_model")
        ValueError: Invalid model ID format: invalid_model
    """
    # Valid pattern: region.provider.model-variant
    # Allows: letters, numbers, dots, hyphens, colons (for versions like :0)
    # Examples:
    #   us.anthropic.claude-sonnet-4-6
    #   us.amazon.nova-lite-v1:0
    pattern = r'^[a-z]{2}\.[a-z][a-z\-]*\.[a-z0-9\-]+(?::[0-9]+)?$'

    if not re.match(pattern, model_id):
        raise ValueError(
            f"Invalid model ID format: '{model_id}'. "
            f"Expected format: region.provider.model (e.g., us.anthropic.claude-sonnet-4-6)"
        )

    return model_id


def validate_temperature(temperature: float) -> float:
    """
    Validate sampling temperature is within valid range.

    Args:
        temperature: Temperature value

    Returns:
        Validated temperature (unchanged if valid)

    Raises:
        ValueError: If temperature is outside [0, 1]
    """
    if not isinstance(temperature, (int, float)):
        raise ValueError(f"Temperature must be a number, got {type(temperature).__name__}")

    if not 0 <= temperature <= 1:
        raise ValueError(f"Temperature must be between 0 and 1, got {temperature}")

    return float(temperature)


def validate_max_tokens(max_tokens: int) -> int:
    """
    Validate max_tokens is a positive integer.

    Args:
        max_tokens: Maximum tokens value

    Returns:
        Validated max_tokens (unchanged if valid)

    Raises:
        ValueError: If max_tokens is not positive
    """
    if not isinstance(max_tokens, int):
        raise ValueError(f"max_tokens must be an integer, got {type(max_tokens).__name__}")

    if max_tokens <= 0:
        raise ValueError(f"max_tokens must be positive, got {max_tokens}")

    return max_tokens
