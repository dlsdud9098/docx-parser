"""
Table formatters package for docx_parser.

This package provides Strategy Pattern implementation for table formatting.
Each formatter converts TableData to a specific output format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type

from .base import TableFormatter
from .html import HtmlTableFormatter
from .json_formatter import JsonTableFormatter
from .markdown import MarkdownTableFormatter
from .text import TextTableFormatter

if TYPE_CHECKING:
    from ..models import HorizontalMergeMode, TableData, TableFormat, VerticalMergeMode

# Registry mapping TableFormat enum to formatter classes
TABLE_FORMATTERS: Dict[str, Type[TableFormatter]] = {
    "markdown": MarkdownTableFormatter,
    "json": JsonTableFormatter,
    "html": HtmlTableFormatter,
    "text": TextTableFormatter,
}


def get_formatter(
    table_format: "TableFormat",
    vertical_merge: "VerticalMergeMode",
    horizontal_merge: "HorizontalMergeMode",
) -> TableFormatter:
    """Get a formatter instance for the specified format.

    Args:
        table_format: The output format (markdown, json, html, text).
        vertical_merge: How to handle vertically merged cells.
        horizontal_merge: How to handle horizontally merged cells.

    Returns:
        TableFormatter instance for the specified format.

    Raises:
        ValueError: If the format is not supported.

    Example:
        >>> from docx_parser.models import TableFormat, VerticalMergeMode, HorizontalMergeMode
        >>> formatter = get_formatter(
        ...     TableFormat.MARKDOWN,
        ...     VerticalMergeMode.REPEAT,
        ...     HorizontalMergeMode.EXPAND
        ... )
        >>> output = formatter.format(table_data)
    """
    format_key = table_format.value if hasattr(table_format, 'value') else str(table_format)
    formatter_class = TABLE_FORMATTERS.get(format_key)

    if formatter_class is None:
        raise ValueError(f"Unsupported table format: {format_key}")

    return formatter_class(vertical_merge, horizontal_merge)


def format_table(
    table_data: "TableData",
    table_format: "TableFormat",
    vertical_merge: "VerticalMergeMode",
    horizontal_merge: "HorizontalMergeMode",
) -> str:
    """Format table data using the specified format.

    Convenience function that creates a formatter and formats in one call.

    Args:
        table_data: The table data to format.
        table_format: The output format.
        vertical_merge: How to handle vertically merged cells.
        horizontal_merge: How to handle horizontally merged cells.

    Returns:
        Formatted table string.

    Example:
        >>> output = format_table(
        ...     table_data,
        ...     TableFormat.HTML,
        ...     VerticalMergeMode.REPEAT,
        ...     HorizontalMergeMode.EXPAND
        ... )
    """
    formatter = get_formatter(table_format, vertical_merge, horizontal_merge)
    return formatter.format(table_data)


__all__ = [
    # Base class
    "TableFormatter",
    # Formatters
    "MarkdownTableFormatter",
    "JsonTableFormatter",
    "HtmlTableFormatter",
    "TextTableFormatter",
    # Registry
    "TABLE_FORMATTERS",
    # Factory functions
    "get_formatter",
    "format_table",
]
