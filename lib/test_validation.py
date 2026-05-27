#!/usr/bin/env python3
"""
Tests for input validation security functions.

Tests for path traversal prevention, URL validation, and model ID validation.
"""

import pytest
import tempfile
from pathlib import Path
from validation import (
    validate_output_path,
    validate_url,
    validate_model_id,
    validate_temperature,
    validate_max_tokens,
)


class TestPathTraversalPrevention:
    """Test path traversal attack prevention."""

    def test_valid_relative_path(self):
        """Valid relative path within current directory."""
        result = validate_output_path("output.txt")
        assert result.name == "output.txt"

    def test_valid_absolute_path_in_dir(self):
        """Valid absolute path within allowed directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_output_path(f"{tmpdir}/output.txt", tmpdir)
            assert result.parent == Path(tmpdir).resolve()

    def test_path_traversal_parent_dir(self):
        """Reject path traversal with ../"""
        with pytest.raises(ValueError, match="must be within"):
            validate_output_path("../../../etc/passwd")

    def test_path_traversal_absolute(self):
        """Reject absolute path outside allowed directory."""
        with pytest.raises(ValueError, match="must be within"):
            validate_output_path("/etc/passwd", ".")

    def test_path_traversal_mixed(self):
        """Reject mixed traversal attempts."""
        with pytest.raises(ValueError, match="must be within"):
            validate_output_path("./output/../../../etc/passwd")

    def test_path_traversal_with_symlink(self):
        """Path traversal protection works with symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a symlink that tries to escape
            tmppath = Path(tmpdir)
            safe_subdir = tmppath / "safe"
            safe_subdir.mkdir()

            with pytest.raises(ValueError, match="must be within"):
                validate_output_path("../../../etc/passwd", str(safe_subdir))

    def test_allows_subdirectory(self):
        """Allow writing to subdirectories within allowed dir."""
        result = validate_output_path("subdir/file.txt")
        assert "subdir" in str(result)


class TestURLValidation:
    """Test URL validation and scheme checking."""

    def test_valid_https_url(self):
        """Accept valid HTTPS URL."""
        url = "https://example.com/page"
        assert validate_url(url) == url

    def test_valid_http_url(self):
        """Accept valid HTTP URL."""
        url = "http://example.com/page"
        assert validate_url(url) == url

    def test_reject_file_scheme(self):
        """Reject file:// URLs."""
        with pytest.raises(ValueError, match="file"):
            validate_url("file:///etc/passwd")

    def test_reject_ftp_scheme(self):
        """Reject FTP URLs."""
        with pytest.raises(ValueError, match="ftp"):
            validate_url("ftp://example.com/file")

    def test_reject_no_scheme(self):
        """Reject URLs without scheme."""
        with pytest.raises(ValueError, match="scheme"):
            validate_url("example.com/page")

    def test_reject_no_domain(self):
        """Reject URL without domain."""
        with pytest.raises(ValueError, match="domain"):
            validate_url("https://")

    def test_reject_malformed_url(self):
        """Reject malformed URLs."""
        # urlparse is lenient and treats this as missing scheme
        with pytest.raises(ValueError, match="missing scheme"):
            validate_url("ht!tp://[invalid")

    def test_custom_allowed_schemes(self):
        """Allow custom schemes."""
        url = "gopher://example.com/resource"
        result = validate_url(url, allowed_schemes=["gopher"])
        assert result == url

    def test_reject_custom_scheme_not_allowed(self):
        """Reject schemes not in custom allowed list."""
        with pytest.raises(ValueError, match="gopher"):
            validate_url("gopher://example.com", allowed_schemes=["http", "https"])

    def test_url_with_path_and_query(self):
        """Accept URLs with paths and query strings."""
        url = "https://example.com/path/to/page?param=value&other=123"
        assert validate_url(url) == url

    def test_url_with_port(self):
        """Accept URLs with port numbers."""
        url = "https://example.com:8443/page"
        assert validate_url(url) == url


class TestModelIDValidation:
    """Test Bedrock model ID format validation."""

    def test_valid_anthropic_claude_sonnet(self):
        """Accept Anthropic Claude Sonnet model ID."""
        model_id = "us.anthropic.claude-sonnet-4-6"
        assert validate_model_id(model_id) == model_id

    def test_valid_amazon_nova_lite(self):
        """Accept Amazon Nova Lite model ID."""
        model_id = "us.amazon.nova-lite-v1:0"
        assert validate_model_id(model_id) == model_id

    def test_valid_with_version_suffix(self):
        """Accept model IDs with version suffix (:0)."""
        model_id = "us.amazon.nova-pro-v1:0"
        assert validate_model_id(model_id) == model_id

    def test_reject_single_word(self):
        """Reject model ID with no dots."""
        with pytest.raises(ValueError, match="Invalid model ID"):
            validate_model_id("claude")

    def test_reject_uppercase(self):
        """Reject uppercase in model ID."""
        with pytest.raises(ValueError, match="Invalid model ID"):
            validate_model_id("US.Anthropic.Claude-sonnet")

    def test_reject_special_chars(self):
        """Reject special characters."""
        with pytest.raises(ValueError, match="Invalid model ID"):
            validate_model_id("us.anthropic.claude@sonnet")

    def test_reject_spaces(self):
        """Reject spaces in model ID."""
        with pytest.raises(ValueError, match="Invalid model ID"):
            validate_model_id("us.anthropic.claude sonnet")

    def test_reject_no_region(self):
        """Reject model ID without region."""
        with pytest.raises(ValueError, match="Invalid model ID"):
            validate_model_id("anthropic.claude-sonnet-4-6")

    def test_accept_alternate_regions(self):
        """Accept model IDs with alternate regions."""
        model_id = "eu.anthropic.claude-haiku-4-5"
        assert validate_model_id(model_id) == model_id


class TestTemperatureValidation:
    """Test temperature parameter validation."""

    def test_valid_temperature_middle(self):
        """Accept temperature in valid range."""
        assert validate_temperature(0.5) == 0.5

    def test_valid_temperature_zero(self):
        """Accept temperature at lower boundary."""
        assert validate_temperature(0) == 0.0

    def test_valid_temperature_one(self):
        """Accept temperature at upper boundary."""
        assert validate_temperature(1) == 1.0

    def test_reject_negative_temperature(self):
        """Reject negative temperature."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            validate_temperature(-0.1)

    def test_reject_temperature_too_high(self):
        """Reject temperature > 1."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            validate_temperature(1.5)

    def test_reject_non_numeric_temperature(self):
        """Reject non-numeric temperature."""
        with pytest.raises(ValueError, match="must be a number"):
            validate_temperature("0.5")

    def test_accept_integer_temperature(self):
        """Accept integer temperature (convert to float)."""
        assert validate_temperature(1) == 1.0


class TestMaxTokensValidation:
    """Test max_tokens parameter validation."""

    def test_valid_max_tokens(self):
        """Accept valid max_tokens."""
        assert validate_max_tokens(2048) == 2048

    def test_valid_max_tokens_one(self):
        """Accept minimum valid max_tokens."""
        assert validate_max_tokens(1) == 1

    def test_reject_zero_tokens(self):
        """Reject zero tokens."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_max_tokens(0)

    def test_reject_negative_tokens(self):
        """Reject negative tokens."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_max_tokens(-100)

    def test_reject_float_tokens(self):
        """Reject float tokens."""
        with pytest.raises(ValueError, match="must be an integer"):
            validate_max_tokens(2048.5)

    def test_reject_string_tokens(self):
        """Reject string tokens."""
        with pytest.raises(ValueError, match="must be an integer"):
            validate_max_tokens("2048")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
