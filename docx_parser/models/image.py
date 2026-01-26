"""
Image-related models for docx_parser.

This module contains ImageInfo and StyleInfo dataclasses.
Separated to avoid circular dependencies with vision module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ImageInfo:
    """Image information with improved structure.

    Attributes:
        index: Image index number (1-based).
        name: Output filename (e.g., "001_image1.png").
        path: Full path to the saved image file.
        original_name: Original filename from DOCX.
        data: Image binary data (for in-memory processing).

    Example:
        >>> info = ImageInfo(index=1, name="001_logo.png", path="/output/001_logo.png")
        >>> info.to_dict()
        {'index': 1, 'name': '001_logo.png', 'path': '/output/001_logo.png', 'original_name': None}
    """
    index: int
    name: str
    path: Optional[str] = None
    original_name: Optional[str] = None
    data: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with index, name, path, and original_name.
            Note: data field is excluded from serialization.
        """
        return {
            "index": self.index,
            "name": self.name,
            "path": self.path,
            "original_name": self.original_name
        }


@dataclass
class StyleInfo:
    """Style information from styles.xml for heading detection.

    Attributes:
        style_id: Style identifier from DOCX.
        name: Human-readable style name.
        outline_level: Heading level (0=H1, 1=H2, ..., 8=H9).
        font_size: Font size in half-points (24 = 12pt).

    Example:
        >>> style = StyleInfo(style_id="Heading1", name="Heading 1", outline_level=0, font_size=32)
        >>> style.outline_level  # H1
        0
    """
    style_id: str
    name: Optional[str] = None
    outline_level: Optional[int] = None
    font_size: Optional[int] = None
