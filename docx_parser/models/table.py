"""
Table models for docx_parser.

This module contains table-related dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TableCell:
    """Represents a table cell with merge information.

    Attributes:
        text: Cell text content.
        colspan: Number of columns this cell spans.
        rowspan: Number of rows this cell spans.
        is_header: Whether this cell is a header cell.
        is_merged_continuation: Whether this cell continues a merge (placeholder).

    Example:
        >>> cell = TableCell(text="Header", colspan=2, is_header=True)
        >>> cell.to_dict()
        {'text': 'Header', 'colspan': 2, 'is_header': True}
    """
    text: str
    colspan: int = 1
    rowspan: int = 1
    is_header: bool = False
    is_merged_continuation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with text and optional merge info.
            Only includes colspan/rowspan/is_header if non-default.
        """
        result: Dict[str, Any] = {"text": self.text}
        if self.colspan > 1:
            result["colspan"] = self.colspan
        if self.rowspan > 1:
            result["rowspan"] = self.rowspan
        if self.is_header:
            result["is_header"] = True
        return result


@dataclass
class TableData:
    """Structured table data.

    Attributes:
        rows: List of rows, each row is a list of TableCell objects.
        col_count: Number of columns in the table.
        row_count: Number of rows in the table.

    Example:
        >>> cells = [[TableCell("A"), TableCell("B")], [TableCell("1"), TableCell("2")]]
        >>> table = TableData(rows=cells, col_count=2, row_count=2)
        >>> table.to_dict()['row_count']
        2
    """
    rows: List[List[TableCell]]
    col_count: int = 0
    row_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with type, rows (as list of cell dicts), col_count, row_count.
        """
        return {
            "type": "table",
            "rows": [
                {"cells": [cell.to_dict() for cell in row]}
                for row in self.rows
            ],
            "col_count": self.col_count,
            "row_count": self.row_count
        }
