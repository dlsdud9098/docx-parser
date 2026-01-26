"""Tests for docx_parser.models.table module."""

import pytest

from docx_parser.models.table import TableCell, TableData


class TestTableCell:
    """Tests for TableCell dataclass."""

    def test_minimal_creation(self):
        """Test creating TableCell with minimal fields."""
        cell = TableCell(text="Hello")
        assert cell.text == "Hello"
        assert cell.colspan == 1
        assert cell.rowspan == 1
        assert cell.is_header is False
        assert cell.is_merged_continuation is False

    def test_full_creation(self):
        """Test creating TableCell with all fields."""
        cell = TableCell(
            text="Header Cell",
            colspan=2,
            rowspan=3,
            is_header=True,
            is_merged_continuation=False
        )
        assert cell.text == "Header Cell"
        assert cell.colspan == 2
        assert cell.rowspan == 3
        assert cell.is_header is True

    def test_merged_continuation(self):
        """Test merged continuation cell."""
        cell = TableCell(text="", is_merged_continuation=True)
        assert cell.is_merged_continuation is True

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        cell = TableCell(text="Data")
        result = cell.to_dict()

        assert result == {"text": "Data"}
        assert "colspan" not in result
        assert "rowspan" not in result
        assert "is_header" not in result

    def test_to_dict_with_colspan(self):
        """Test to_dict with colspan > 1."""
        cell = TableCell(text="Wide", colspan=3)
        result = cell.to_dict()

        assert result == {"text": "Wide", "colspan": 3}

    def test_to_dict_with_rowspan(self):
        """Test to_dict with rowspan > 1."""
        cell = TableCell(text="Tall", rowspan=2)
        result = cell.to_dict()

        assert result == {"text": "Tall", "rowspan": 2}

    def test_to_dict_with_header(self):
        """Test to_dict with is_header True."""
        cell = TableCell(text="Column", is_header=True)
        result = cell.to_dict()

        assert result == {"text": "Column", "is_header": True}

    def test_to_dict_excludes_merged_continuation(self):
        """Test that is_merged_continuation is not included in to_dict."""
        cell = TableCell(text="", is_merged_continuation=True)
        result = cell.to_dict()

        assert "is_merged_continuation" not in result

    def test_to_dict_full(self):
        """Test to_dict with all non-default fields."""
        cell = TableCell(
            text="Big Header",
            colspan=4,
            rowspan=2,
            is_header=True
        )
        result = cell.to_dict()

        assert result == {
            "text": "Big Header",
            "colspan": 4,
            "rowspan": 2,
            "is_header": True
        }

    def test_empty_text(self):
        """Test cell with empty text."""
        cell = TableCell(text="")
        assert cell.text == ""
        assert cell.to_dict() == {"text": ""}

    def test_unicode_text(self):
        """Test Korean/Unicode text."""
        cell = TableCell(text="안녕하세요")
        assert cell.text == "안녕하세요"

    def test_multiline_text(self):
        """Test cell with multiline text."""
        cell = TableCell(text="Line 1\nLine 2")
        assert cell.text == "Line 1\nLine 2"


class TestTableData:
    """Tests for TableData dataclass."""

    def test_minimal_creation(self):
        """Test creating TableData with minimal fields."""
        cells = [[TableCell(text="A")]]
        table = TableData(rows=cells)

        assert len(table.rows) == 1
        assert table.col_count == 0
        assert table.row_count == 0

    def test_with_counts(self):
        """Test creating TableData with counts."""
        cells = [
            [TableCell(text="A"), TableCell(text="B")],
            [TableCell(text="1"), TableCell(text="2")]
        ]
        table = TableData(rows=cells, col_count=2, row_count=2)

        assert table.col_count == 2
        assert table.row_count == 2

    def test_empty_table(self):
        """Test empty table."""
        table = TableData(rows=[])
        assert table.rows == []
        assert table.to_dict()["rows"] == []

    def test_to_dict_structure(self):
        """Test to_dict basic structure."""
        cells = [[TableCell(text="Data")]]
        table = TableData(rows=cells, col_count=1, row_count=1)
        result = table.to_dict()

        assert result["type"] == "table"
        assert "rows" in result
        assert result["col_count"] == 1
        assert result["row_count"] == 1

    def test_to_dict_nested_cells(self):
        """Test to_dict correctly nests cell data."""
        cells = [
            [TableCell(text="A"), TableCell(text="B")],
            [TableCell(text="1"), TableCell(text="2")]
        ]
        table = TableData(rows=cells, col_count=2, row_count=2)
        result = table.to_dict()

        assert len(result["rows"]) == 2
        assert result["rows"][0]["cells"][0]["text"] == "A"
        assert result["rows"][0]["cells"][1]["text"] == "B"
        assert result["rows"][1]["cells"][0]["text"] == "1"
        assert result["rows"][1]["cells"][1]["text"] == "2"

    def test_to_dict_with_merged_cells(self):
        """Test to_dict with merged cells."""
        cells = [
            [TableCell(text="Header", colspan=2, is_header=True)],
            [TableCell(text="A"), TableCell(text="B")]
        ]
        table = TableData(rows=cells, col_count=2, row_count=2)
        result = table.to_dict()

        first_row = result["rows"][0]["cells"]
        assert len(first_row) == 1
        assert first_row[0]["colspan"] == 2
        assert first_row[0]["is_header"] is True

    def test_to_dict_format(self):
        """Test to_dict output format matches expected structure."""
        cells = [[TableCell(text="Test")]]
        table = TableData(rows=cells, col_count=1, row_count=1)
        result = table.to_dict()

        expected_format = {
            "type": "table",
            "rows": [
                {"cells": [{"text": "Test"}]}
            ],
            "col_count": 1,
            "row_count": 1
        }
        assert result == expected_format

    def test_3x3_table(self):
        """Test 3x3 table structure."""
        cells = [
            [TableCell(text=f"{r}{c}") for c in range(3)]
            for r in range(3)
        ]
        table = TableData(rows=cells, col_count=3, row_count=3)
        result = table.to_dict()

        assert len(result["rows"]) == 3
        assert len(result["rows"][0]["cells"]) == 3
        assert result["rows"][1]["cells"][2]["text"] == "12"
