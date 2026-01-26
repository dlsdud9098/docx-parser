"""
Utility modules for docx_parser.

This package contains pure utility functions and constants.
No imports from other docx_parser modules to avoid circular dependencies.
"""

from .xml import (
    NAMESPACES,
    METADATA_NAMESPACES,
    XMLNamespaces,
)
from .image import (
    IMAGE_SIGNATURES,
    detect_image_format,
    convert_image_to_png,
    process_image,
    get_mime_type,
)

__all__ = [
    # XML utilities
    "NAMESPACES",
    "METADATA_NAMESPACES",
    "XMLNamespaces",
    # Image utilities
    "IMAGE_SIGNATURES",
    "detect_image_format",
    "convert_image_to_png",
    "process_image",
    "get_mime_type",
]
