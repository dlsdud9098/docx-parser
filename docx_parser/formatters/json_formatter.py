"""
JSON table formatter.

Converts TableData to JSON format with full merge information preserved.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import TableFormatter

if TYPE_CHECKING:
    from ..models import TableData


class JsonTableFormatter(TableFormatter):
    """Formatter that converts TableData to JSON format.

    Preserves all merge information (colspan, rowspan) in the output.

    Example:
        >>> formatter = JsonTableFormatter(
        ...     vertical_merge=VerticalMergeMode.REPEAT,
        ...     horizontal_merge=HorizontalMergeMode.EXPAND
        ... )
        >>> json_table = formatter.format(table_data)
        >>> data = json.loads(json_table)
    """

    def format(self, table_data: "TableData") -> str:
        """Convert TableData to JSON format.

        Args:
            table_data: The table data to format.

        Returns:
            JSON string representation of the table.
        """
        return json.dumps(table_data.to_dict(), ensure_ascii=False)
