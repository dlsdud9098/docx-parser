"""
Unit tests for vision module.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest

from docx_parser.vision import (
    ImageEncoder,
    EncodedImage,
    VisionProvider,
    ImageDescription,
    VisionError,
    ProviderNotInstalledError,
    APIKeyNotFoundError,
    ImageProcessingError,
    RateLimitError,
    RetryConfig,
    RetryHandler,
    with_retry,
    retry_on_rate_limit,
    calculate_delay,
    encode_image_base64,
    encode_image_data_uri,
    get_image_info,
    get_image_mime_type,
)


# ============================================================================
# Test Data
# ============================================================================

# PNG magic bytes
PNG_DATA = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

# JPEG magic bytes
JPEG_DATA = b"\xff\xd8\xff\xe0" + b"\x00" * 100

# GIF magic bytes
GIF_DATA = b"GIF89a" + b"\x00" * 100

# WEBP magic bytes (RIFF header + WEBP)
WEBP_DATA = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 100

# BMP magic bytes
BMP_DATA = b"BM" + b"\x00" * 100


# ============================================================================
# ImageEncoder Tests
# ============================================================================


class TestImageEncoder:
    """Tests for ImageEncoder class."""

    def test_encode_png_from_bytes(self):
        """Test encoding PNG from bytes."""
        encoder = ImageEncoder()
        result = encoder.encode(PNG_DATA)

        assert isinstance(result, EncodedImage)
        assert result.mime_type == "image/png"
        assert len(result.base64_data) > 0
        assert result.original_size == len(PNG_DATA)

    def test_encode_jpeg_from_bytes(self):
        """Test encoding JPEG from bytes."""
        encoder = ImageEncoder()
        result = encoder.encode(JPEG_DATA)

        assert result.mime_type == "image/jpeg"

    def test_encode_gif_from_bytes(self):
        """Test encoding GIF from bytes."""
        encoder = ImageEncoder()
        result = encoder.encode(GIF_DATA)

        assert result.mime_type == "image/gif"

    def test_encode_webp_from_bytes(self):
        """Test encoding WEBP from bytes."""
        encoder = ImageEncoder()
        result = encoder.encode(WEBP_DATA)

        assert result.mime_type == "image/webp"

    def test_encode_bmp_from_bytes(self):
        """Test encoding BMP from bytes."""
        encoder = ImageEncoder()
        result = encoder.encode(BMP_DATA)

        assert result.mime_type == "image/bmp"

    def test_encode_from_bytesio(self):
        """Test encoding from BytesIO."""
        encoder = ImageEncoder()
        buffer = io.BytesIO(PNG_DATA)
        result = encoder.encode(buffer)

        assert result.mime_type == "image/png"

    def test_encode_from_file(self, tmp_path):
        """Test encoding from file path."""
        encoder = ImageEncoder()
        image_path = tmp_path / "test.png"
        image_path.write_bytes(PNG_DATA)

        result = encoder.encode(image_path)

        assert result.mime_type == "image/png"
        assert result.original_size == len(PNG_DATA)

    def test_data_uri_property(self):
        """Test data_uri property."""
        encoder = ImageEncoder()
        result = encoder.encode(PNG_DATA)

        assert result.data_uri.startswith("data:image/png;base64,")

    def test_encode_to_data_uri(self):
        """Test encode_to_data_uri method."""
        encoder = ImageEncoder()
        uri = encoder.encode_to_data_uri(PNG_DATA)

        assert uri.startswith("data:image/png;base64,")

    def test_encode_for_anthropic(self):
        """Test encode_for_anthropic method."""
        encoder = ImageEncoder()
        base64_data, mime_type = encoder.encode_for_anthropic(PNG_DATA)

        assert mime_type == "image/png"
        assert len(base64_data) > 0

    def test_detect_mime_type_from_magic_bytes(self):
        """Test MIME type detection from magic bytes."""
        encoder = ImageEncoder()

        assert encoder.detect_mime_type(PNG_DATA) == "image/png"
        assert encoder.detect_mime_type(JPEG_DATA) == "image/jpeg"
        assert encoder.detect_mime_type(GIF_DATA) == "image/gif"
        assert encoder.detect_mime_type(WEBP_DATA) == "image/webp"
        assert encoder.detect_mime_type(BMP_DATA) == "image/bmp"

    def test_detect_mime_type_from_filename(self):
        """Test MIME type detection from filename."""
        encoder = ImageEncoder()
        unknown_data = b"\x00\x00\x00\x00"

        assert encoder.detect_mime_type(unknown_data, "image.jpg") == "image/jpeg"
        assert encoder.detect_mime_type(unknown_data, "image.png") == "image/png"

    def test_detect_mime_type_default(self):
        """Test default MIME type for unknown data."""
        encoder = ImageEncoder(default_mime_type="image/png")
        unknown_data = b"\x00\x00\x00\x00"

        assert encoder.detect_mime_type(unknown_data) == "image/png"


class TestEncodeFunctions:
    """Tests for module-level encoding functions."""

    def test_encode_image_base64(self):
        """Test encode_image_base64 function."""
        result = encode_image_base64(PNG_DATA)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_image_data_uri(self):
        """Test encode_image_data_uri function."""
        result = encode_image_data_uri(PNG_DATA)
        assert result.startswith("data:image/png;base64,")

    def test_get_image_info(self):
        """Test get_image_info function."""
        base64_data, mime_type = get_image_info(PNG_DATA)
        assert mime_type == "image/png"
        assert len(base64_data) > 0

    def test_get_image_mime_type(self):
        """Test get_image_mime_type function."""
        assert get_image_mime_type(PNG_DATA) == "image/png"
        assert get_image_mime_type(JPEG_DATA) == "image/jpeg"


# ============================================================================
# RetryConfig Tests
# ============================================================================


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.jitter is False

    def test_custom_exceptions(self):
        """Test custom retryable exceptions."""
        config = RetryConfig(
            retryable_exceptions=(ValueError, TypeError)
        )

        assert ValueError in config.retryable_exceptions
        assert TypeError in config.retryable_exceptions


# ============================================================================
# calculate_delay Tests
# ============================================================================


class TestCalculateDelay:
    """Tests for calculate_delay function."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        # attempt 0: 1 * (2^0) = 1
        assert calculate_delay(0, 1.0, 60.0, 2.0, False) == 1.0

        # attempt 1: 1 * (2^1) = 2
        assert calculate_delay(1, 1.0, 60.0, 2.0, False) == 2.0

        # attempt 2: 1 * (2^2) = 4
        assert calculate_delay(2, 1.0, 60.0, 2.0, False) == 4.0

    def test_max_delay_cap(self):
        """Test max delay capping."""
        # Very large attempt should be capped
        delay = calculate_delay(10, 1.0, 10.0, 2.0, False)
        assert delay == 10.0

    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness."""
        delays = set()
        for _ in range(10):
            delay = calculate_delay(0, 1.0, 60.0, 2.0, True)
            delays.add(round(delay, 3))

        # With jitter, we should get different values
        assert len(delays) > 1


# ============================================================================
# with_retry Decorator Tests
# ============================================================================


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""

    def test_success_no_retry(self):
        """Test successful call without retry."""
        call_count = 0

        @with_retry(max_retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self):
        """Test retry on exception."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01, jitter=False)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("test")
            return "success"

        result = failing_then_success()

        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test exception raised after max retries."""
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RateLimitError("test")

        with pytest.raises(RateLimitError):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_non_retryable_exception(self):
        """Test non-retryable exception is not retried."""
        call_count = 0

        @with_retry(
            max_retries=3,
            retryable_exceptions=(RateLimitError,),
        )
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # No retry

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        retry_calls = []

        @with_retry(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
            on_retry=lambda e, a: retry_calls.append((str(e), a)),
        )
        def fails_then_succeeds():
            if len(retry_calls) < 2:
                raise RateLimitError("test")
            return "success"

        result = fails_then_succeeds()

        assert result == "success"
        assert len(retry_calls) == 2


class TestRetryOnRateLimit:
    """Tests for retry_on_rate_limit decorator."""

    def test_retries_rate_limit_error(self):
        """Test retry on RateLimitError."""
        call_count = 0

        @retry_on_rate_limit(max_retries=2, base_delay=0.01)
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("test")
            return "success"

        result = rate_limited()

        assert result == "success"
        assert call_count == 2


# ============================================================================
# RetryHandler Tests
# ============================================================================


class TestRetryHandler:
    """Tests for RetryHandler class."""

    def test_execute_success(self):
        """Test successful execution."""
        handler = RetryHandler()
        result = handler.execute(lambda: "success")

        assert result == "success"
        assert handler.total_attempts == 1

    def test_execute_with_retry(self):
        """Test execution with retries."""
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("test")
            return "success"

        result = handler.execute(failing_func)

        assert result == "success"
        assert handler.total_attempts == 3

    def test_execute_all_fail(self):
        """Test execution when all attempts fail."""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)

        with pytest.raises(RateLimitError):
            handler.execute(lambda: (_ for _ in ()).throw(RateLimitError("test")))

        assert handler.total_attempts == 3
        assert handler.last_exception is not None

    def test_reset(self):
        """Test handler reset."""
        handler = RetryHandler()
        handler.attempts = 5
        handler.last_exception = Exception("test")

        handler.reset()

        assert handler.attempts == 0
        assert handler.last_exception is None


# ============================================================================
# Exception Tests
# ============================================================================


class TestExceptions:
    """Tests for vision exceptions."""

    def test_vision_error_base(self):
        """Test VisionError base class."""
        error = VisionError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_provider_not_installed_error(self):
        """Test ProviderNotInstalledError."""
        error = ProviderNotInstalledError("OpenAI", "openai")

        assert error.provider == "OpenAI"
        assert error.package == "openai"
        assert "openai" in str(error)
        assert "pip install" in str(error)

    def test_api_key_not_found_error(self):
        """Test APIKeyNotFoundError."""
        error = APIKeyNotFoundError("OpenAI", "OPENAI_API_KEY")

        assert error.provider == "OpenAI"
        assert error.env_var == "OPENAI_API_KEY"
        assert "OPENAI_API_KEY" in str(error)

    def test_image_processing_error(self):
        """Test ImageProcessingError."""
        error = ImageProcessingError("/path/to/image.png", "file not found")

        assert error.image_path == "/path/to/image.png"
        assert error.reason == "file not found"
        assert "image.png" in str(error)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("OpenAI", retry_after=60)

        assert error.provider == "OpenAI"
        assert error.retry_after == 60
        assert "rate limit" in str(error).lower()
        assert "60" in str(error)

    def test_rate_limit_error_no_retry_after(self):
        """Test RateLimitError without retry_after."""
        error = RateLimitError("OpenAI")

        assert error.retry_after is None


# ============================================================================
# ImageDescription Tests
# ============================================================================


class TestImageDescription:
    """Tests for ImageDescription dataclass."""

    def test_minimal_creation(self):
        """Test minimal creation."""
        desc = ImageDescription(index=1, description="A test image")

        assert desc.index == 1
        assert desc.description == "A test image"
        assert desc.confidence is None
        assert desc.tokens_used is None

    def test_full_creation(self):
        """Test full creation."""
        desc = ImageDescription(
            index=1,
            description="A test image",
            confidence=0.95,
            tokens_used=150,
        )

        assert desc.confidence == 0.95
        assert desc.tokens_used == 150


# ============================================================================
# VisionProvider Base Tests
# ============================================================================


class TestVisionProviderBase:
    """Tests for VisionProvider base class."""

    def test_default_prompt_korean(self):
        """Test Korean default prompt."""
        # Create a mock concrete provider
        class MockProvider(VisionProvider):
            @property
            def default_model(self):
                return "mock-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                return "description"

            def _encode_image(self, image_path):
                return "encoded"

        provider = MockProvider(language="ko")
        assert "한국어" in provider.prompt or "설명" in provider.prompt

    def test_default_prompt_english(self):
        """Test English default prompt."""
        class MockProvider(VisionProvider):
            @property
            def default_model(self):
                return "mock-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                return "description"

            def _encode_image(self, image_path):
                return "encoded"

        provider = MockProvider(language="en")
        assert "describe" in provider.prompt.lower()

    def test_custom_prompt(self):
        """Test custom prompt."""
        class MockProvider(VisionProvider):
            @property
            def default_model(self):
                return "mock-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                return "description"

            def _encode_image(self, image_path):
                return "encoded"

        provider = MockProvider(prompt="Custom prompt here")
        assert provider.prompt == "Custom prompt here"


# ============================================================================
# OpenAI Vision Provider Tests
# ============================================================================


class TestOpenAIVisionProvider:
    """Tests for OpenAI Vision Provider."""

    def test_provider_not_installed(self):
        """Test error when openai package not installed."""
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(Exception):
                from docx_parser.vision.openai import OpenAIVisionProvider
                OpenAIVisionProvider()

    def test_api_key_not_found(self, monkeypatch):
        """Test error when API key not provided."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        try:
            from docx_parser.vision.openai import OpenAIVisionProvider

            with patch("openai.OpenAI"):
                with pytest.raises(APIKeyNotFoundError):
                    OpenAIVisionProvider(api_key=None)
        except ImportError:
            pytest.skip("openai package not installed")

    def test_provider_initialization(self, monkeypatch):
        """Test provider initialization with API key."""
        try:
            from docx_parser.vision.openai import OpenAIVisionProvider

            with patch("openai.OpenAI") as mock_client:
                provider = OpenAIVisionProvider(api_key="test-key")

                assert provider.api_key == "test-key"
                assert provider.provider_name == "openai"
                assert provider.default_model == "gpt-4o"
        except ImportError:
            pytest.skip("openai package not installed")

    def test_describe_image_success(self, tmp_path, sample_image_bytes):
        """Test successful image description."""
        try:
            from docx_parser.vision.openai import OpenAIVisionProvider

            # Create test image file
            img_path = tmp_path / "test.png"
            img_path.write_bytes(sample_image_bytes)

            with patch("openai.OpenAI") as mock_openai_class:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "A test image"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai_class.return_value = mock_client

                provider = OpenAIVisionProvider(api_key="test-key")
                result = provider.describe_image(img_path)

                assert result == "A test image"
                mock_client.chat.completions.create.assert_called_once()
        except ImportError:
            pytest.skip("openai package not installed")

    def test_describe_image_rate_limit(self, tmp_path, sample_image_bytes):
        """Test rate limit error handling."""
        try:
            import openai
            from docx_parser.vision.openai import OpenAIVisionProvider

            img_path = tmp_path / "test.png"
            img_path.write_bytes(sample_image_bytes)

            with patch("openai.OpenAI") as mock_openai_class:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = openai.RateLimitError(
                    "rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={}
                )
                mock_openai_class.return_value = mock_client

                provider = OpenAIVisionProvider(api_key="test-key")

                with pytest.raises(RateLimitError):
                    provider.describe_image(img_path)
        except ImportError:
            pytest.skip("openai package not installed")


# ============================================================================
# Anthropic Vision Provider Tests
# ============================================================================


class TestAnthropicVisionProvider:
    """Tests for Anthropic Vision Provider."""

    def test_api_key_not_found(self, monkeypatch):
        """Test error when API key not provided."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        try:
            from docx_parser.vision.anthropic import AnthropicVisionProvider

            with patch("anthropic.Anthropic"):
                with pytest.raises(APIKeyNotFoundError):
                    AnthropicVisionProvider(api_key=None)
        except ImportError:
            pytest.skip("anthropic package not installed")

    def test_provider_initialization(self, monkeypatch):
        """Test provider initialization with API key."""
        try:
            from docx_parser.vision.anthropic import AnthropicVisionProvider

            with patch("anthropic.Anthropic") as mock_client:
                provider = AnthropicVisionProvider(api_key="test-key")

                assert provider.api_key == "test-key"
                assert provider.provider_name == "anthropic"
        except ImportError:
            pytest.skip("anthropic package not installed")

    def test_describe_image_success(self, tmp_path, sample_image_bytes):
        """Test successful image description."""
        try:
            from docx_parser.vision.anthropic import AnthropicVisionProvider

            img_path = tmp_path / "test.png"
            img_path.write_bytes(sample_image_bytes)

            with patch("anthropic.Anthropic") as mock_anthropic_class:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.content = [MagicMock()]
                mock_response.content[0].text = "A test image"
                mock_client.messages.create.return_value = mock_response
                mock_anthropic_class.return_value = mock_client

                provider = AnthropicVisionProvider(api_key="test-key")
                result = provider.describe_image(img_path)

                assert result == "A test image"
        except ImportError:
            pytest.skip("anthropic package not installed")


# ============================================================================
# Google Vision Provider Tests
# ============================================================================


class TestGoogleVisionProvider:
    """Tests for Google Vision Provider."""

    def test_api_key_not_found(self, monkeypatch):
        """Test error when API key not provided."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        try:
            from docx_parser.vision.google import GoogleVisionProvider

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.GenerativeModel"):
                    with pytest.raises(APIKeyNotFoundError):
                        GoogleVisionProvider(api_key=None)
        except ImportError:
            pytest.skip("google-generativeai package not installed")

    def test_provider_initialization(self, monkeypatch):
        """Test provider initialization with API key."""
        try:
            from docx_parser.vision.google import GoogleVisionProvider

            with patch("google.generativeai.configure") as mock_configure:
                with patch("google.generativeai.GenerativeModel") as mock_model:
                    provider = GoogleVisionProvider(api_key="test-key")

                    assert provider.api_key == "test-key"
                    assert provider.provider_name == "google"
                    mock_configure.assert_called_once_with(api_key="test-key")
        except ImportError:
            pytest.skip("google-generativeai package not installed")


# ============================================================================
# Utils/Image Tests for Coverage
# ============================================================================


class TestImageUtilsCoverage:
    """Additional tests for image utilities coverage."""

    def test_encode_unknown_format(self):
        """Test encoding unknown image format."""
        encoder = ImageEncoder()
        # Unknown binary data
        unknown_data = b"\x00\x01\x02\x03" + b"\x00" * 100

        result = encoder.encode(unknown_data)
        # Should fall back to octet-stream
        assert result.mime_type in ["application/octet-stream", "image/png"]

    def test_encode_from_path_object(self, tmp_path, sample_image_bytes):
        """Test encoding from Path object."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(sample_image_bytes)

        encoder = ImageEncoder()
        result = encoder.encode(img_path)

        assert isinstance(result, EncodedImage)
        assert result.mime_type == "image/png"

    def test_encode_from_bytesio(self, sample_image_bytes):
        """Test encoding from BytesIO."""
        encoder = ImageEncoder()
        buffer = io.BytesIO(sample_image_bytes)

        result = encoder.encode(buffer)

        assert isinstance(result, EncodedImage)


# ============================================================================
# Vision Utils Module Tests
# ============================================================================


class TestVisionUtilsModule:
    """Tests for docx_parser.vision.utils module."""

    def test_encode_image_base64_from_bytes(self, sample_image_bytes):
        """Test base64 encoding from bytes."""
        from docx_parser.vision.utils import encode_image_base64

        result = encode_image_base64(sample_image_bytes)
        assert isinstance(result, str)
        # Should be valid base64
        import base64
        decoded = base64.b64decode(result)
        assert decoded == sample_image_bytes

    def test_encode_image_base64_from_bytesio(self, sample_image_bytes):
        """Test base64 encoding from BytesIO."""
        from docx_parser.vision.utils import encode_image_base64

        buffer = io.BytesIO(sample_image_bytes)
        result = encode_image_base64(buffer)
        assert isinstance(result, str)

    def test_encode_image_base64_from_path(self, tmp_path, sample_image_bytes):
        """Test base64 encoding from file path."""
        from docx_parser.vision.utils import encode_image_base64

        img_path = tmp_path / "test.png"
        img_path.write_bytes(sample_image_bytes)

        result = encode_image_base64(img_path)
        assert isinstance(result, str)

    def test_get_image_mime_type_png_bytes(self, sample_image_bytes):
        """Test MIME type detection for PNG bytes."""
        from docx_parser.vision.utils import get_image_mime_type

        result = get_image_mime_type(sample_image_bytes)
        assert result == "image/png"

    def test_get_image_mime_type_jpeg_bytes(self, sample_jpeg_bytes):
        """Test MIME type detection for JPEG bytes."""
        from docx_parser.vision.utils import get_image_mime_type

        result = get_image_mime_type(sample_jpeg_bytes)
        assert result == "image/jpeg"

    def test_get_image_mime_type_gif_bytes(self):
        """Test MIME type detection for GIF bytes."""
        from docx_parser.vision.utils import get_image_mime_type

        gif_data = b'GIF89a' + b'\x00' * 100
        result = get_image_mime_type(gif_data)
        assert result == "image/gif"

    def test_get_image_mime_type_webp_bytes(self):
        """Test MIME type detection for WebP bytes."""
        from docx_parser.vision.utils import get_image_mime_type

        webp_data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        result = get_image_mime_type(webp_data)
        assert result == "image/webp"

    def test_get_image_mime_type_bmp_bytes(self):
        """Test MIME type detection for BMP bytes."""
        from docx_parser.vision.utils import get_image_mime_type

        bmp_data = b'BM' + b'\x00' * 100
        result = get_image_mime_type(bmp_data)
        assert result == "image/bmp"

    def test_get_image_mime_type_from_bytesio(self, sample_image_bytes):
        """Test MIME type detection from BytesIO."""
        from docx_parser.vision.utils import get_image_mime_type

        buffer = io.BytesIO(sample_image_bytes)
        result = get_image_mime_type(buffer)
        assert result == "image/png"

    def test_get_image_mime_type_from_filename(self):
        """Test MIME type from filename when magic bytes unknown."""
        from docx_parser.vision.utils import get_image_mime_type

        unknown_data = b'\x00\x00\x00\x00' * 10
        result = get_image_mime_type(unknown_data, filename="test.jpg")
        assert result == "image/jpeg"

    def test_get_image_mime_type_from_path(self, tmp_path, sample_image_bytes):
        """Test MIME type detection from file path."""
        from docx_parser.vision.utils import get_image_mime_type

        img_path = tmp_path / "test.png"
        img_path.write_bytes(sample_image_bytes)

        result = get_image_mime_type(img_path)
        assert result == "image/png"

    def test_get_image_mime_type_from_path_unknown_ext(self, tmp_path):
        """Test MIME type from path with unknown extension."""
        from docx_parser.vision.utils import get_image_mime_type

        # Use unknown binary data with unknown extension
        unknown_data = b'\x00\x00\x00\x00' * 10
        img_path = tmp_path / "test.unknownext123"
        img_path.write_bytes(unknown_data)

        result = get_image_mime_type(img_path)
        # Should fallback to image/png for truly unknown types
        # mimetypes may return None for unknown extensions, leading to image/png fallback
        assert result in ["image/png", "application/octet-stream"] or result.startswith("image/")

    def test_encode_image_data_uri(self, sample_image_bytes):
        """Test data URI encoding."""
        from docx_parser.vision.utils import encode_image_data_uri

        result = encode_image_data_uri(sample_image_bytes)
        assert result.startswith("data:image/png;base64,")

    def test_encode_image_data_uri_with_filename(self):
        """Test data URI encoding with filename."""
        from docx_parser.vision.utils import encode_image_data_uri

        jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
        result = encode_image_data_uri(jpeg_data, filename="test.jpg")
        assert result.startswith("data:image/jpeg;base64,")

    def test_get_image_info(self, sample_image_bytes):
        """Test get_image_info returns tuple."""
        from docx_parser.vision.utils import get_image_info

        base64_data, mime_type = get_image_info(sample_image_bytes)
        assert isinstance(base64_data, str)
        assert mime_type == "image/png"


# ============================================================================
# Vision Module Factory Tests
# ============================================================================


class TestVisionFactory:
    """Tests for vision module factory functions."""

    def test_create_vision_provider_openai(self, monkeypatch):
        """Test creating OpenAI provider via factory."""
        try:
            from docx_parser.vision import create_vision_provider

            with patch("openai.OpenAI") as mock_client:
                provider = create_vision_provider("openai", api_key="test-key")
                assert provider is not None
                assert provider.provider_name == "openai"
        except ImportError:
            pytest.skip("openai package not installed")

    def test_create_vision_provider_anthropic(self, monkeypatch):
        """Test creating Anthropic provider via factory."""
        try:
            from docx_parser.vision import create_vision_provider

            with patch("anthropic.Anthropic") as mock_client:
                provider = create_vision_provider("anthropic", api_key="test-key")
                assert provider is not None
                assert provider.provider_name == "anthropic"
        except ImportError:
            pytest.skip("anthropic package not installed")

    def test_create_vision_provider_google(self, monkeypatch):
        """Test creating Google provider via factory."""
        try:
            from docx_parser.vision import create_vision_provider

            with patch("google.generativeai.configure"):
                with patch("google.generativeai.GenerativeModel"):
                    provider = create_vision_provider("google", api_key="test-key")
                    assert provider is not None
                    assert provider.provider_name == "google"
        except ImportError:
            pytest.skip("google-generativeai package not installed")

    def test_create_vision_provider_unknown(self):
        """Test error for unknown provider."""
        from docx_parser.vision import create_vision_provider

        with pytest.raises(ValueError, match="Unknown provider"):
            create_vision_provider("unknown_provider")

    def test_lazy_import_openai_provider(self):
        """Test lazy import of OpenAI provider class."""
        try:
            from docx_parser import vision
            cls = getattr(vision, "OpenAIVisionProvider")
            assert cls is not None
        except ImportError:
            pytest.skip("openai package not installed")

    def test_lazy_import_anthropic_provider(self):
        """Test lazy import of Anthropic provider class."""
        try:
            from docx_parser import vision
            cls = getattr(vision, "AnthropicVisionProvider")
            assert cls is not None
        except ImportError:
            pytest.skip("anthropic package not installed")

    def test_lazy_import_unknown_attribute(self):
        """Test error for unknown attribute."""
        from docx_parser import vision

        with pytest.raises(AttributeError):
            _ = getattr(vision, "UnknownClass")


# ============================================================================
# Vision Base Class Tests
# ============================================================================


class TestVisionProviderBaseClass:
    """Tests for VisionProvider base class methods."""

    def test_default_prompt_japanese(self):
        """Test Japanese default prompt."""
        class MockProvider(VisionProvider):
            @property
            def default_model(self):
                return "mock-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                return "description"

            def _encode_image(self, image_path):
                return "encoded"

        provider = MockProvider(language="ja")
        assert "日本語" in provider.prompt or "説明" in provider.prompt or "describe" in provider.prompt.lower()

    def test_model_property(self):
        """Test model property returns configured model."""
        class MockProvider(VisionProvider):
            @property
            def default_model(self):
                return "default-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                return "description"

            def _encode_image(self, image_path):
                return "encoded"

        provider = MockProvider(model="custom-model")
        assert provider.model == "custom-model"

        provider2 = MockProvider()
        assert provider2.model == "default-model"


class TestVisionProviderDescribeImages:
    """Tests for VisionProvider.describe_images method."""

    def _create_mock_provider(self, describe_result="description"):
        """Create a mock provider for testing."""
        class MockProvider(VisionProvider):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.describe_calls = []

            @property
            def default_model(self):
                return "mock-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                self.describe_calls.append((image, prompt))
                if isinstance(describe_result, Exception):
                    raise describe_result
                return describe_result

            def _encode_image(self, image_path):
                return "encoded"

        return MockProvider()

    def test_describe_images_with_path(self, tmp_path, sample_image_bytes):
        """Test describe_images when images have path."""
        from docx_parser.models import ImageInfo

        img_path = tmp_path / "test.png"
        img_path.write_bytes(sample_image_bytes)

        provider = self._create_mock_provider("A test image")
        images = [ImageInfo(index=1, name="test.png", path=str(img_path))]

        result = provider.describe_images(images)

        assert result == {1: "A test image"}
        assert len(provider.describe_calls) == 1

    def test_describe_images_with_data(self, sample_image_bytes):
        """Test describe_images when images have data but no path."""
        from docx_parser.models import ImageInfo

        provider = self._create_mock_provider("Image from data")
        images = [ImageInfo(index=1, name="test.png", path=None, data=sample_image_bytes)]

        result = provider.describe_images(images)

        assert result == {1: "Image from data"}

    def test_describe_images_skips_no_data(self):
        """Test describe_images skips images with no path and no data."""
        from docx_parser.models import ImageInfo

        provider = self._create_mock_provider("Should not be called")
        images = [ImageInfo(index=1, name="test.png", path=None, data=None)]

        result = provider.describe_images(images)

        assert result == {}
        assert len(provider.describe_calls) == 0

    def test_describe_images_with_error(self, tmp_path, sample_image_bytes):
        """Test describe_images handles errors gracefully."""
        from docx_parser.models import ImageInfo

        img_path = tmp_path / "test.png"
        img_path.write_bytes(sample_image_bytes)

        provider = self._create_mock_provider(Exception("API Error"))
        images = [ImageInfo(index=1, name="test.png", path=str(img_path))]

        result = provider.describe_images(images)

        assert 1 in result
        assert "이미지 처리 실패" in result[1]
        assert "API Error" in result[1]

    def test_describe_images_with_custom_prompts(self, tmp_path, sample_image_bytes):
        """Test describe_images with custom prompts per image."""
        from docx_parser.models import ImageInfo

        img1 = tmp_path / "test1.png"
        img2 = tmp_path / "test2.png"
        img1.write_bytes(sample_image_bytes)
        img2.write_bytes(sample_image_bytes)

        provider = self._create_mock_provider("description")
        images = [
            ImageInfo(index=1, name="test1.png", path=str(img1)),
            ImageInfo(index=2, name="test2.png", path=str(img2)),
        ]

        result = provider.describe_images(images, {1: "Custom prompt for image 1"})

        assert len(result) == 2
        # Check that custom prompt was passed for image 1
        assert provider.describe_calls[0][1] == "Custom prompt for image 1"
        # Default (None) for image 2
        assert provider.describe_calls[1][1] is None

    def test_describe_images_multiple(self, tmp_path, sample_image_bytes):
        """Test describe_images with multiple images."""
        from docx_parser.models import ImageInfo

        images = []
        for i in range(3):
            img_path = tmp_path / f"test{i}.png"
            img_path.write_bytes(sample_image_bytes)
            images.append(ImageInfo(index=i+1, name=f"test{i}.png", path=str(img_path)))

        provider = self._create_mock_provider("description")
        result = provider.describe_images(images)

        assert len(result) == 3
        assert all(v == "description" for v in result.values())


class TestVisionProviderLanguagePrompts:
    """Tests for VisionProvider language-specific prompts."""

    def _create_provider(self, language):
        """Create a mock provider with specified language."""
        class MockProvider(VisionProvider):
            @property
            def default_model(self):
                return "mock-model"

            @property
            def provider_name(self):
                return "mock"

            def describe_image(self, image, prompt=None):
                return "description"

            def _encode_image(self, image_path):
                return "encoded"

        return MockProvider(language=language)

    def test_chinese_prompt(self):
        """Test Chinese prompt."""
        provider = self._create_provider("zh")
        assert "请" in provider.prompt or "图片" in provider.prompt

    def test_unknown_language_defaults_to_english(self):
        """Test unknown language defaults to English prompt."""
        provider = self._create_provider("xx")
        assert "describe" in provider.prompt.lower()


# ============================================================================
# Transformers Vision Provider Tests
# ============================================================================


class TestTransformersVisionProvider:
    """Tests for TransformersVisionProvider with mocked dependencies."""

    def test_provider_not_installed_error(self):
        """Test ProviderNotInstalledError when transformers not installed."""
        import sys

        # Save and remove modules
        saved_modules = {}
        modules_to_mock = ['torch', 'transformers', 'PIL']
        for mod in modules_to_mock:
            if mod in sys.modules:
                saved_modules[mod] = sys.modules[mod]

        try:
            # Clear the transformers provider from cache
            if 'docx_parser.vision.transformers' in sys.modules:
                del sys.modules['docx_parser.vision.transformers']

            # Mock import to raise ImportError
            with patch.dict(sys.modules, {'torch': None}):
                with pytest.raises(ProviderNotInstalledError):
                    from docx_parser.vision.transformers import TransformersVisionProvider
                    TransformersVisionProvider(model_id="test")
        except TypeError:
            # Some Python versions handle module mocking differently
            pytest.skip("Cannot properly mock module imports")
        finally:
            # Restore
            for mod, value in saved_modules.items():
                sys.modules[mod] = value

    def test_create_transformers_provider_via_factory(self):
        """Test creating transformers provider via factory function."""
        try:
            import torch
            import transformers
            from PIL import Image
            # Check if AutoModelForVision2Seq is available
            from transformers import AutoModelForVision2Seq
        except (ImportError, AttributeError):
            pytest.skip("torch/transformers/PIL or AutoModelForVision2Seq not available")

        from docx_parser.vision import create_vision_provider

        with patch('torch.cuda.is_available', return_value=False):
            with patch('transformers.AutoProcessor.from_pretrained') as mock_proc:
                with patch('transformers.AutoModelForVision2Seq.from_pretrained') as mock_model:
                    mock_proc.return_value = MagicMock()
                    mock_model.return_value = MagicMock()

                    try:
                        provider = create_vision_provider(
                            "transformers",
                            model="test-model"
                        )
                        assert provider is not None
                        assert provider.provider_name == "transformers"
                    except ProviderNotInstalledError:
                        pytest.skip("Transformers not properly installed")

    def test_transformers_model_types_constant(self):
        """Test MODEL_TYPES constant is defined."""
        try:
            from docx_parser.vision.transformers import TransformersVisionProvider
            assert hasattr(TransformersVisionProvider, 'MODEL_TYPES')
            assert 'llava' in TransformersVisionProvider.MODEL_TYPES
            assert 'qwen' in TransformersVisionProvider.MODEL_TYPES
        except (ImportError, ProviderNotInstalledError):
            pytest.skip("transformers not installed")
