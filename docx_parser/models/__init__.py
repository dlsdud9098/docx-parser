"""
Models package for docx_parser.

This module contains all data models, enums, and dataclasses used by the parser.
"""

from .enums import (
    VerticalMergeMode,
    HorizontalMergeMode,
    OutputFormat,
    HierarchyMode,
    TableFormat,
    BlockType,
)
from .image import ImageInfo, StyleInfo
from .blocks import ParagraphBlock, HeadingBlock, TableBlock, ImageBlock
from .metadata import CoreMetadata, AppMetadata, DocxMetadata
from .table import TableCell, TableData
from .result import ParseResult

# Type alias
from .enums import HeadingPattern

__all__ = [
    # Enums
    "VerticalMergeMode",
    "HorizontalMergeMode",
    "OutputFormat",
    "HierarchyMode",
    "TableFormat",
    "BlockType",
    # Type alias
    "HeadingPattern",
    # Image
    "ImageInfo",
    "StyleInfo",
    # Blocks
    "ParagraphBlock",
    "HeadingBlock",
    "TableBlock",
    "ImageBlock",
    # Metadata
    "CoreMetadata",
    "AppMetadata",
    "DocxMetadata",
    # Table
    "TableCell",
    "TableData",
    # Result
    "ParseResult",
]
