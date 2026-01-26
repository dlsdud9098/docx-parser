"""
Table processing for DOCX files.

Handles parsing of table elements and conversion to various formats.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from ..formatters import format_table
from ..models import (
    HorizontalMergeMode,
    TableBlock,
    TableCell,
    TableData,
    TableFormat,
    VerticalMergeMode,
)
from ..utils.xml import NAMESPACES
from .base import ParsingContext, Processor

logger = logging.getLogger(__name__)


class TableProcessor(Processor):
    """
    Processor for parsing and converting tables from DOCX files.

    Handles:
    - Parsing table XML elements to TableData
    - Converting to markdown, HTML, JSON, or text formats
    - Managing cell merging (vertical and horizontal)
    """

    def __init__(
        self,
        vertical_merge: VerticalMergeMode = VerticalMergeMode.REPEAT,
        horizontal_merge: HorizontalMergeMode = HorizontalMergeMode.EXPAND,
        table_format: TableFormat = TableFormat.MARKDOWN,
        namespaces: Optional[dict] = None,
    ) -> None:
        """
        Initialize table processor.

        Args:
            vertical_merge: How to handle vertically merged cells.
            horizontal_merge: How to handle horizontally merged cells.
            table_format: Output format for tables.
            namespaces: Optional custom namespace dictionary.
        """
        self._vertical_merge = vertical_merge
        self._horizontal_merge = horizontal_merge
        self._table_format = table_format
        self._namespaces = namespaces or NAMESPACES

    def process(self, context: ParsingContext, **kwargs: Any) -> str:
        """
        Process a table element from context.

        Args:
            context: ParsingContext (not used directly).
            **kwargs: Must include 'element' with the table XML element.

        Returns:
            Formatted table string.
        """
        element = kwargs.get("element")
        if element is None:
            return ""
        return self.parse_table(element)

    def parse_table_data(self, elem: ET.Element) -> TableData:
        """
        Parse a table element to structured TableData with merge info preserved.

        Args:
            elem: Table XML element.

        Returns:
            TableData containing parsed table structure.
        """
        ns = self._namespaces
        w_ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

        rows: List[List[TableCell]] = []
        vmerge_info: Dict[int, Dict[str, Any]] = {}  # col_idx -> {text, start_row, rowspan}

        row_idx = 0
        for row in elem.findall(".//w:tr", ns):
            row_cells: List[TableCell] = []
            col_idx = 0

            for cell in row.findall(".//w:tc", ns):
                # Extract text from each paragraph
                paragraphs = []
                for para in cell.findall(".//w:p", ns):
                    para_text = "".join(
                        t.text or "" for t in para.findall(".//w:t", ns)
                    ).strip()
                    if para_text:
                        paragraphs.append(para_text)
                cell_text = "\n".join(paragraphs)

                # Get cell properties
                tcPr = cell.find("w:tcPr", ns)
                colspan = 1
                vmerge_type = None

                if tcPr is not None:
                    gs = tcPr.find("w:gridSpan", ns)
                    if gs is not None:
                        colspan = int(gs.get(w_ns + "val", "1"))

                    vm = tcPr.find("w:vMerge", ns)
                    if vm is not None:
                        vmerge_type = vm.get(w_ns + "val", "continue")

                # Handle vertical merge tracking
                is_merged_continuation = False
                rowspan = 1

                if vmerge_type == "restart":
                    # Start of vertical merge
                    vmerge_info[col_idx] = {
                        "text": cell_text,
                        "start_row": row_idx,
                        "rowspan": 1,
                    }
                elif vmerge_type == "continue":
                    # Continue vertical merge
                    is_merged_continuation = True
                    if col_idx in vmerge_info:
                        vmerge_info[col_idx]["rowspan"] += 1
                    cell_text = ""  # Merged cell has no text
                else:
                    # No vertical merge - finalize any previous merge
                    if col_idx in vmerge_info:
                        del vmerge_info[col_idx]

                # Create cell
                row_cells.append(
                    TableCell(
                        text=cell_text,
                        colspan=colspan,
                        rowspan=rowspan,
                        is_header=(row_idx == 0),
                        is_merged_continuation=is_merged_continuation,
                    )
                )
                col_idx += colspan

            if row_cells:
                rows.append(row_cells)
                row_idx += 1

        # Update rowspan values for cells that start vertical merges
        for col_idx, info in vmerge_info.items():
            start_row = info["start_row"]
            rowspan = info["rowspan"]
            if start_row < len(rows):
                # Find the cell at that position
                current_col = 0
                for cell in rows[start_row]:
                    if current_col == col_idx:
                        cell.rowspan = rowspan
                        break
                    current_col += cell.colspan

        col_count = max((sum(c.colspan for c in row) for row in rows), default=0)

        return TableData(rows=rows, col_count=col_count, row_count=len(rows))

    def parse_table(self, elem: ET.Element) -> str:
        """
        Parse a table element to the configured format.

        Args:
            elem: Table XML element.

        Returns:
            Formatted table string.
        """
        table_data = self.parse_table_data(elem)

        # Use formatters module
        return format_table(
            table_data,
            self._table_format,
            self._vertical_merge,
            self._horizontal_merge,
        )

    def parse_table_block(self, elem: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Parse a table element to a content block for JSON output.

        Args:
            elem: Table XML element.

        Returns:
            TableBlock dictionary or None if empty.
        """
        table_data = self.parse_table_data(elem)
        if not table_data.rows:
            return None

        # Convert to simple rows format
        rows = []
        headers = None

        for row_idx, row in enumerate(table_data.rows):
            row_texts = []
            for cell in row:
                if not cell.is_merged_continuation:
                    row_texts.append(cell.text)
            if row_texts:
                rows.append(row_texts)

        # First row as headers if present
        if rows:
            headers = rows[0]
            rows = rows[1:] if len(rows) > 1 else []

        return TableBlock(
            rows=rows,
            headers=headers,
            metadata={"col_count": table_data.col_count, "row_count": table_data.row_count},
        ).to_dict()


@staticmethod
def escape_table_cell(text: str) -> str:
    """
    Escape special characters for markdown table cells.

    Handles:
    - Backslash (\\) -> (\\\\) - must be first to avoid double-escaping
    - Pipe (|) -> (\\|) - table cell delimiter
    - Asterisk (*) -> (\\*) - italic/bold marker
    - Underscore (_) -> (\\_) - italic/bold marker
    - Backtick (`) -> (\\`) - code marker
    - Newlines -> <br> - preserves multi-line content in table cells

    Args:
        text: Cell text to escape.

    Returns:
        Escaped text safe for markdown tables.
    """
    if not text:
        return text
    # Order matters: escape backslash first, then other special chars
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("*", "\\*")
    text = text.replace("_", "\\_")
    text = text.replace("`", "\\`")
    # Replace newlines with <br> to preserve multi-line content
    text = text.replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")
    return text
