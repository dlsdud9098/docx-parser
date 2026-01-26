"""
Enums for docx_parser.

This module contains all enumeration types used throughout the parser.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Tuple


class VerticalMergeMode(str, Enum):
    """How to handle vertically merged cells.

    Attributes:
        REPEAT: Repeat the value in merged cells.
        EMPTY: Keep merged cells empty.
        FIRST_ONLY: Only show value in first cell.
    """
    REPEAT = "repeat"
    EMPTY = "empty"
    FIRST_ONLY = "first"


class HorizontalMergeMode(str, Enum):
    """How to handle horizontally merged cells.

    Attributes:
        EXPAND: Expand to multiple empty cells.
        SINGLE: Keep as single cell (ignore span).
        REPEAT: Repeat value in spanned cells.
    """
    EXPAND = "expand"
    SINGLE = "single"
    REPEAT = "repeat"


class OutputFormat(str, Enum):
    """Output format for parsed content.

    Attributes:
        MARKDOWN: Default Markdown format with tables.
        TEXT: Plain text (no markdown formatting).
        JSON: Structured JSON output.
    """
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


class HierarchyMode(str, Enum):
    """How to detect heading hierarchy.

    Attributes:
        NONE: No heading detection (default, backward compatible).
        AUTO: Style first, font_size fallback.
        STYLE: Use styles.xml outlineLevel only.
        FONT_SIZE: Use font size only.
        PATTERN: Use custom text patterns (e.g., "I. ", "1. ", "1)").
    """
    NONE = "none"
    AUTO = "auto"
    STYLE = "style"
    FONT_SIZE = "font_size"
    PATTERN = "pattern"


class TableFormat(str, Enum):
    """Output format for tables.

    Attributes:
        MARKDOWN: Markdown table (default).
        JSON: Structured JSON with merge info.
        HTML: HTML table with colspan/rowspan.
        TEXT: Tab-separated text.
    """
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"


class BlockType(str, Enum):
    """Content block types for structured JSON output.

    Attributes:
        PARAGRAPH: Paragraph content block.
        HEADING: Heading content block.
        TABLE: Table content block.
        IMAGE: Image content block.
    """
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"


# Type alias for heading patterns: list of (pattern, header_level)
# Example: [("I. ", 1), ("1. ", 2), ("1)", 3), ("(1)", 4)]
HeadingPattern = List[Tuple[str, int]]
