"""
HTML table formatter.

Converts TableData to HTML table format with proper colspan/rowspan attributes.
"""

from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from .base import TableFormatter

if TYPE_CHECKING:
    from ..models import TableData


class HtmlTableFormatter(TableFormatter):
    """Formatter that converts TableData to HTML table format.

    Supports colspan and rowspan attributes for merged cells.

    Example:
        >>> formatter = HtmlTableFormatter(
        ...     vertical_merge=VerticalMergeMode.REPEAT,
        ...     horizontal_merge=HorizontalMergeMode.EXPAND
        ... )
        >>> html_table = formatter.format(table_data)
        >>> print(html_table)
        <table>
          <tr>
            <td colspan="2">Merged</td>
          </tr>
        </table>
    """

    def format(self, table_data: "TableData") -> str:
        """Convert TableData to HTML format with colspan/rowspan.

        Args:
            table_data: The table data to format.

        Returns:
            HTML table string.
        """
        if not table_data.rows:
            return ""

        html_parts = ["<table>"]

        # Track cells to skip due to rowspan
        skip_cells: Dict[tuple, bool] = {}  # (row_idx, col_idx) -> True

        for row_idx, row in enumerate(table_data.rows):
            html_parts.append("  <tr>")
            col_idx = 0

            for cell in row:
                # Skip cells covered by rowspan
                while (row_idx, col_idx) in skip_cells:
                    col_idx += 1

                if cell.is_merged_continuation:
                    col_idx += cell.colspan
                    continue

                tag = "th" if cell.is_header else "td"
                attrs = []

                if cell.colspan > 1:
                    attrs.append(f'colspan="{cell.colspan}"')
                if cell.rowspan > 1:
                    attrs.append(f'rowspan="{cell.rowspan}"')
                    # Mark cells to skip in subsequent rows
                    for r in range(row_idx + 1, row_idx + cell.rowspan):
                        for c in range(col_idx, col_idx + cell.colspan):
                            skip_cells[(r, c)] = True

                attr_str = " " + " ".join(attrs) if attrs else ""
                text = self._escape_cell(cell.text)
                html_parts.append(f"    <{tag}{attr_str}>{text}</{tag}>")

                col_idx += cell.colspan

            html_parts.append("  </tr>")

        html_parts.append("</table>")
        return "\n".join(html_parts)

    def _escape_cell(self, text: str) -> str:
        """Escape HTML special characters and convert newlines.

        Args:
            text: Cell text to escape.

        Returns:
            HTML-escaped text with newlines as <br>.
        """
        # Basic HTML escaping
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('\n', '<br>')
        return text
