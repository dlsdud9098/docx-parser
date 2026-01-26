"""
Base classes and protocols for table formatters.

This module defines the TableFormatter protocol that all formatters must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import HorizontalMergeMode, TableData, VerticalMergeMode


class TableFormatter(ABC):
    """Abstract base class for table formatters.

    All table formatters must implement the `format` method to convert
    TableData to a string representation.

    Attributes:
        vertical_merge: How to handle vertically merged cells.
        horizontal_merge: How to handle horizontally merged cells.

    Example:
        >>> formatter = MarkdownTableFormatter(
        ...     vertical_merge=VerticalMergeMode.REPEAT,
        ...     horizontal_merge=HorizontalMergeMode.EXPAND
        ... )
        >>> output = formatter.format(table_data)
    """

    def __init__(
        self,
        vertical_merge: "VerticalMergeMode",
        horizontal_merge: "HorizontalMergeMode",
    ):
        """Initialize formatter with merge modes.

        Args:
            vertical_merge: How to handle vertically merged cells.
            horizontal_merge: How to handle horizontally merged cells.
        """
        self.vertical_merge = vertical_merge
        self.horizontal_merge = horizontal_merge

    @abstractmethod
    def format(self, table_data: "TableData") -> str:
        """Convert TableData to formatted string.

        Args:
            table_data: The table data to format.

        Returns:
            Formatted string representation of the table.
        """
        pass

    def _escape_cell(self, text: str) -> str:
        """Escape special characters in cell text.

        Override this method in subclasses for format-specific escaping.

        Args:
            text: Cell text to escape.

        Returns:
            Escaped text.
        """
        return text
