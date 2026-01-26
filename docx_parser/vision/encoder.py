"""
Image encoding utilities for vision providers.

Provides a unified ImageEncoder class that handles encoding images
for different vision API providers.
"""

from __future__ import annotations

import base64
import io
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)


# Image format magic bytes signatures
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ("image/png", "png"),
    b"\xff\xd8\xff": ("image/jpeg", "jpg"),
    b"GIF87a": ("image/gif", "gif"),
    b"GIF89a": ("image/gif", "gif"),
    b"RIFF": ("image/webp", "webp"),  # Need to check bytes 8-12 for WEBP
    b"BM": ("image/bmp", "bmp"),
    b"II*\x00": ("image/tiff", "tiff"),  # Little-endian TIFF
    b"MM\x00*": ("image/tiff", "tiff"),  # Big-endian TIFF
}

# Extension to MIME type mapping
EXTENSION_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


@dataclass
class EncodedImage:
    """
    Result of image encoding.

    Attributes:
        base64_data: Base64-encoded image data.
        mime_type: MIME type of the image.
        data_uri: Full data URI (data:mime_type;base64,data).
        original_size: Original image size in bytes.
    """

    base64_data: str
    mime_type: str
    original_size: int

    @property
    def data_uri(self) -> str:
        """Get the complete data URI."""
        return f"data:{self.mime_type};base64,{self.base64_data}"


class ImageEncoder:
    """
    Unified image encoder for vision providers.

    Handles encoding images from various sources (Path, bytes, BytesIO)
    into formats suitable for different API providers.

    Example:
        encoder = ImageEncoder()

        # From file path
        encoded = encoder.encode(Path("image.png"))
        print(encoded.data_uri)  # data:image/png;base64,...

        # From bytes
        encoded = encoder.encode(image_bytes, filename="image.jpg")
        print(encoded.mime_type)  # image/jpeg

        # Get base64 and mime separately (for Anthropic)
        base64_data, mime_type = encoder.encode_for_anthropic(image_bytes)
    """

    def __init__(self, default_mime_type: str = "image/png") -> None:
        """
        Initialize the encoder.

        Args:
            default_mime_type: Default MIME type when detection fails.
        """
        self._default_mime_type = default_mime_type

    def encode(
        self,
        image: Union[Path, bytes, io.BytesIO],
        filename: Optional[str] = None,
    ) -> EncodedImage:
        """
        Encode an image to base64 with MIME type detection.

        Args:
            image: Image source (Path, bytes, or BytesIO).
            filename: Optional filename for MIME type detection.

        Returns:
            EncodedImage with base64 data and detected MIME type.
        """
        # Read image data
        data = self._read_image_data(image)

        # Detect MIME type
        mime_type = self.detect_mime_type(data, filename or self._get_filename(image))

        # Encode to base64
        base64_data = base64.standard_b64encode(data).decode("utf-8")

        return EncodedImage(
            base64_data=base64_data,
            mime_type=mime_type,
            original_size=len(data),
        )

    def encode_to_data_uri(
        self,
        image: Union[Path, bytes, io.BytesIO],
        filename: Optional[str] = None,
    ) -> str:
        """
        Encode image to data URI format (for OpenAI).

        Args:
            image: Image source.
            filename: Optional filename for MIME type detection.

        Returns:
            Data URI string (data:mime_type;base64,...).
        """
        encoded = self.encode(image, filename)
        return encoded.data_uri

    def encode_for_anthropic(
        self,
        image: Union[Path, bytes, io.BytesIO],
        filename: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Encode image for Anthropic API (separate base64 and MIME type).

        Args:
            image: Image source.
            filename: Optional filename for MIME type detection.

        Returns:
            Tuple of (base64_data, mime_type).
        """
        encoded = self.encode(image, filename)
        return encoded.base64_data, encoded.mime_type

    def detect_mime_type(
        self,
        data: bytes,
        filename: Optional[str] = None,
    ) -> str:
        """
        Detect MIME type from image data using magic bytes.

        Args:
            data: Image data bytes.
            filename: Optional filename for fallback detection.

        Returns:
            Detected MIME type string.
        """
        # Check magic bytes
        for signature, (mime_type, _) in IMAGE_SIGNATURES.items():
            if signature == b"RIFF":
                # Special handling for WEBP (need to check bytes 8-12)
                if data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
                    return "image/webp"
            elif data.startswith(signature):
                return mime_type

        # Fallback to filename extension
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in EXTENSION_MIME_MAP:
                return EXTENSION_MIME_MAP[ext]

        # Use mimetypes for Path-based detection
        if filename:
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                return mime_type

        logger.debug(f"Could not detect MIME type, using default: {self._default_mime_type}")
        return self._default_mime_type

    def _read_image_data(self, image: Union[Path, bytes, io.BytesIO]) -> bytes:
        """
        Read image data from various sources.

        Args:
            image: Image source.

        Returns:
            Image data as bytes.
        """
        if isinstance(image, bytes):
            return image
        elif isinstance(image, io.BytesIO):
            return image.getvalue()
        else:
            with open(image, "rb") as f:
                return f.read()

    def _get_filename(self, image: Union[Path, bytes, io.BytesIO]) -> Optional[str]:
        """
        Get filename from image source if available.

        Args:
            image: Image source.

        Returns:
            Filename string or None.
        """
        if isinstance(image, Path):
            return image.name
        return None


# Module-level convenience functions for backward compatibility
def encode_image_base64(image: Union[Path, bytes, io.BytesIO]) -> str:
    """
    Encode image to base64.

    Args:
        image: Image source.

    Returns:
        Base64-encoded string.
    """
    encoder = ImageEncoder()
    return encoder.encode(image).base64_data


def encode_image_data_uri(
    image: Union[Path, bytes, io.BytesIO],
    filename: Optional[str] = None,
) -> str:
    """
    Encode image to data URI format.

    Args:
        image: Image source.
        filename: Optional filename for MIME detection.

    Returns:
        Data URI string.
    """
    encoder = ImageEncoder()
    return encoder.encode_to_data_uri(image, filename)


def get_image_info(
    image: Union[Path, bytes, io.BytesIO],
    filename: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Get image base64 and MIME type.

    Args:
        image: Image source.
        filename: Optional filename for MIME detection.

    Returns:
        Tuple of (base64_data, mime_type).
    """
    encoder = ImageEncoder()
    return encoder.encode_for_anthropic(image, filename)


def get_image_mime_type(
    image: Union[Path, bytes, io.BytesIO],
    filename: Optional[str] = None,
) -> str:
    """
    Detect image MIME type.

    Args:
        image: Image source.
        filename: Optional filename for fallback.

    Returns:
        MIME type string.
    """
    encoder = ImageEncoder()
    if isinstance(image, bytes):
        data = image
    elif isinstance(image, io.BytesIO):
        data = image.getvalue()
    else:
        with open(image, "rb") as f:
            data = f.read()
    return encoder.detect_mime_type(data, filename)
