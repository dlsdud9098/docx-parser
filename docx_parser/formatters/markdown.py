"""
Markdown table formatter.

Converts TableData to GitHub-flavored Markdown table format.
"""

from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from .base import TableFormatter

if TYPE_CHECKING:
    from ..models import HorizontalMergeMode, TableData, VerticalMergeMode


class MarkdownTableFormatter(TableFormatter):
    """Formatter that converts TableData to Markdown table format.

    Supports vertical and horizontal merge modes for cell handling.

    Example:
        >>> formatter = MarkdownTableFormatter(
        ...     vertical_merge=VerticalMergeMode.REPEAT,
        ...     horizontal_merge=HorizontalMergeMode.EXPAND
        ... )
        >>> md_table = formatter.format(table_data)
        >>> print(md_table)
        | Col1 | Col2 |
        | --- | --- |
        | A | B |
    """

    def __init__(
        self,
        vertical_merge: "VerticalMergeMode",
        horizontal_merge: "HorizontalMergeMode",
    ):
        """Initialize Markdown formatter.

        Args:
            vertical_merge: How to handle vertically merged cells.
            horizontal_merge: How to handle horizontally merged cells.
        """
        super().__init__(vertical_merge, horizontal_merge)
        # Import here to avoid circular imports
        from ..models import HorizontalMergeMode, VerticalMergeMode
        self._VerticalMergeMode = VerticalMergeMode
        self._HorizontalMergeMode = HorizontalMergeMode

    def format(self, table_data: "TableData") -> str:
        """Convert TableData to Markdown format.

        Args:
            table_data: The table data to format.

        Returns:
            Markdown table string.
        """
        if not table_data.rows:
            return ""

        # Expand cells based on vertical/horizontal merge modes
        expanded_rows: List[List[str]] = []
        vmerge_values: Dict[int, str] = {}

        for row_idx, row in enumerate(table_data.rows):
            expanded_row: List[str] = []
            col_idx = 0

            for cell in row:
                text = cell.text.replace('\n', '<br>')

                # Handle vertical merge based on mode
                if cell.is_merged_continuation:
                    if self.vertical_merge == self._VerticalMergeMode.REPEAT:
                        text = vmerge_values.get(col_idx, '')
                    elif self.vertical_merge == self._VerticalMergeMode.EMPTY:
                        text = ''
                    elif self.vertical_merge == self._VerticalMergeMode.FIRST_ONLY:
                        text = ''
                elif cell.rowspan > 1:
                    vmerge_values[col_idx] = text

                # Handle horizontal merge based on mode
                if self.horizontal_merge == self._HorizontalMergeMode.EXPAND:
                    expanded_row.append(text)
                    for _ in range(cell.colspan - 1):
                        expanded_row.append('')
                elif self.horizontal_merge == self._HorizontalMergeMode.SINGLE:
                    expanded_row.append(text)
                elif self.horizontal_merge == self._HorizontalMergeMode.REPEAT:
                    for _ in range(cell.colspan):
                        expanded_row.append(text)

                col_idx += cell.colspan

            expanded_rows.append(expanded_row)

        if not expanded_rows:
            return ""

        # Normalize column count
        max_cols = max(len(row) for row in expanded_rows)
        for row in expanded_rows:
            while len(row) < max_cols:
                row.append('')

        # Convert to markdown
        md_rows = []
        for row in expanded_rows:
            escaped_cells = [self._escape_cell(cell) for cell in row]
            md_rows.append("| " + " | ".join(escaped_cells) + " |")

        header_sep = "| " + " | ".join(["---"] * max_cols) + " |"
        return md_rows[0] + "\n" + header_sep + "\n" + "\n".join(md_rows[1:])

    def _escape_cell(self, text: str) -> str:
        """Escape pipe characters in cell text for Markdown tables.

        Args:
            text: Cell text to escape.

        Returns:
            Text with pipe characters escaped.
        """
        return text.replace('|', '\\|')
