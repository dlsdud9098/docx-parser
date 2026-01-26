"""
Plain text table formatter.

Converts TableData to tab-separated text format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import TableFormatter

if TYPE_CHECKING:
    from ..models import TableData


class TextTableFormatter(TableFormatter):
    """Formatter that converts TableData to tab-separated text format.

    Simplified output without merge information, suitable for plain text.

    Example:
        >>> formatter = TextTableFormatter(
        ...     vertical_merge=VerticalMergeMode.REPEAT,
        ...     horizontal_merge=HorizontalMergeMode.EXPAND
        ... )
        >>> text_table = formatter.format(table_data)
        >>> print(text_table)
        Col1    Col2
        A       B
    """

    def format(self, table_data: "TableData") -> str:
        """Convert TableData to tab-separated text format.

        Args:
            table_data: The table data to format.

        Returns:
            Tab-separated text string.
        """
        if not table_data.rows:
            return ""

        lines = []
        for row in table_data.rows:
            cells = []
            for cell in row:
                if not cell.is_merged_continuation:
                    text = self._escape_cell(cell.text)
                    cells.append(text)
            lines.append("\t".join(cells))

        return "\n".join(lines)

    def _escape_cell(self, text: str) -> str:
        """Remove newlines and tabs from cell text.

        Args:
            text: Cell text to clean.

        Returns:
            Text with newlines and tabs replaced by spaces.
        """
        return text.replace('\n', ' ').replace('\t', ' ')
