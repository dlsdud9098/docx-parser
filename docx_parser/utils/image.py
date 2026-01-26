"""
Image utilities for docx_parser.

This module contains image format detection, conversion, and MIME type utilities.
Consolidates image-related functions from parser.py and vision/utils.py.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Tuple, Union

# Magic bytes for image format detection
IMAGE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'png',
    b'\xff\xd8\xff': 'jpeg',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'BM': 'bmp',
    b'II*\x00': 'tiff',  # Little-endian TIFF
    b'MM\x00*': 'tiff',  # Big-endian TIFF
    b'RIFF': 'webp',     # WebP (need to check further)
    b'II\xbc\x01': 'wdp',  # JPEG XR / HD Photo / WDP
    b'\x01\x00\x00\x00': 'emf',  # EMF (simplified)
    b'\xd7\xcd\xc6\x9a': 'wmf',  # WMF
}

# MIME type mapping for common image formats
MIME_TYPE_MAP = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.wdp': 'image/vnd.ms-photo',
    '.hdp': 'image/vnd.ms-photo',
    '.jxr': 'image/jxr',
}

# Format to MIME type mapping
FORMAT_TO_MIME = {
    'png': 'image/png',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'wdp': 'image/vnd.ms-photo',
    'emf': 'image/x-emf',
    'wmf': 'image/x-wmf',
}


def detect_image_format(data: bytes) -> Optional[str]:
    """Detect image format from magic bytes.

    Args:
        data: Image binary data.

    Returns:
        Format string ('png', 'jpeg', 'gif', 'wdp', 'emf', 'wmf', etc.) or None.

    Example:
        >>> with open('image.png', 'rb') as f:
        ...     fmt = detect_image_format(f.read())
        >>> fmt
        'png'
    """
    for signature, fmt in IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            # Special check for WebP (RIFF....WEBP)
            if fmt == 'webp' and len(data) >= 12:
                if data[8:12] != b'WEBP':
                    continue
            return fmt
    return None


def get_mime_type(
    image: Union[Path, bytes, io.BytesIO],
    filename: Optional[str] = None
) -> str:
    """Get MIME type for an image.

    Detects MIME type from magic bytes first, then falls back to filename extension.

    Args:
        image: Image as file path, bytes, or BytesIO object.
        filename: Optional filename for extension-based detection (for bytes/BytesIO).

    Returns:
        MIME type string (e.g., 'image/png').

    Example:
        >>> get_mime_type(Path('logo.png'))
        'image/png'
        >>> get_mime_type(b'\\x89PNG\\r\\n\\x1a\\n...')
        'image/png'
    """
    # Get binary data for magic byte detection
    if isinstance(image, bytes):
        data = image
    elif isinstance(image, io.BytesIO):
        data = image.getvalue()
    elif isinstance(image, Path):
        try:
            with open(image, 'rb') as f:
                data = f.read(32)  # Only read header for detection
        except (IOError, OSError):
            data = b''
        filename = str(image)
    else:
        data = b''

    # Try magic byte detection first
    fmt = detect_image_format(data)
    if fmt and fmt in FORMAT_TO_MIME:
        return FORMAT_TO_MIME[fmt]

    # Fall back to filename extension
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[ext]

    # Default to PNG
    return 'image/png'


def _convert_wdp_to_png(data: bytes) -> Optional[bytes]:
    """Convert WDP/JPEG XR to PNG using JxrDecApp (if available).

    Args:
        data: WDP image binary data.

    Returns:
        PNG data if successful, None if conversion failed.
    """
    import shutil
    import subprocess
    import tempfile

    # Check if JxrDecApp is available
    if not shutil.which('JxrDecApp'):
        return None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            wdp_path = Path(tmpdir) / 'input.wdp'
            bmp_path = Path(tmpdir) / 'output.bmp'

            # Write WDP file
            with open(wdp_path, 'wb') as f:
                f.write(data)

            # Convert WDP to BMP using JxrDecApp
            result = subprocess.run(
                ['JxrDecApp', '-i', str(wdp_path), '-o', str(bmp_path)],
                capture_output=True,
                timeout=30
            )

            if result.returncode != 0 or not bmp_path.exists():
                return None

            # Convert BMP to PNG using PIL
            from PIL import Image

            img = Image.open(bmp_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()

    except Exception:
        return None


def convert_image_to_png(data: bytes, original_ext: str) -> Tuple[bytes, str]:
    """Convert image data to PNG format if needed.

    Args:
        data: Original image binary data.
        original_ext: Original file extension (e.g., '.wdp', '.tmp').

    Returns:
        Tuple of (converted_data, new_extension).
        If conversion fails or not needed, returns original data with original ext.

    Example:
        >>> data, ext = convert_image_to_png(wdp_data, '.wdp')
        >>> ext
        '.png'
    """
    ext_lower = original_ext.lower()

    # Already PNG or common web formats - no conversion needed
    if ext_lower in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return data, original_ext

    # Detect actual format for .tmp files
    if ext_lower == '.tmp':
        detected = detect_image_format(data)
        if detected in ('png', 'jpeg', 'gif', 'webp'):
            # It's already a standard format, just fix extension
            new_ext = '.jpg' if detected == 'jpeg' else f'.{detected}'
            return data, new_ext

    # WDP/HDP (JPEG XR) - use JxrDecApp if available
    if ext_lower in ('.wdp', '.hdp', '.jxr'):
        png_data = _convert_wdp_to_png(data)
        if png_data:
            return png_data, '.png'
        # Fall through to PIL attempt

    # Convert using PIL
    try:
        from PIL import Image

        # Try to open and convert
        img = Image.open(io.BytesIO(data))

        # Convert to RGB if necessary (for RGBA or palette images)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Save as PNG
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue(), '.png'

    except Exception:
        # Conversion failed (unsupported format), return original
        return data, original_ext


def process_image(
    data: bytes,
    original_name: str,
    convert_to_png: bool = True
) -> Tuple[bytes, str]:
    """Process image: detect format, convert if needed.

    Args:
        data: Image binary data.
        original_name: Original filename.
        convert_to_png: Whether to convert non-standard formats to PNG.

    Returns:
        Tuple of (processed_data, new_filename).

    Example:
        >>> data, name = process_image(raw_data, 'image.wdp')
        >>> name
        'image.png'
    """
    original_path = Path(original_name)
    original_ext = original_path.suffix.lower()
    stem = original_path.stem

    if not convert_to_png:
        return data, original_name

    # Convert if needed
    new_data, new_ext = convert_image_to_png(data, original_ext)

    if new_ext != original_ext:
        new_name = stem + new_ext
        return new_data, new_name

    return data, original_name
