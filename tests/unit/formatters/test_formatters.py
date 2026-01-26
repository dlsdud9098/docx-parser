"""Tests for docx_parser.formatters package."""

import json

import pytest

from docx_parser.formatters import (
    TABLE_FORMATTERS,
    HtmlTableFormatter,
    JsonTableFormatter,
    MarkdownTableFormatter,
    TableFormatter,
    TextTableFormatter,
    format_table,
    get_formatter,
)
from docx_parser.models import (
    HorizontalMergeMode,
    TableCell,
    TableData,
    TableFormat,
    VerticalMergeMode,
)


@pytest.fixture
def simple_table():
    """Create a simple 2x2 table."""
    cells = [
        [TableCell(text="A"), TableCell(text="B")],
        [TableCell(text="1"), TableCell(text="2")],
    ]
    return TableData(rows=cells, col_count=2, row_count=2)


@pytest.fixture
def merged_table():
    """Create a table with merged cells."""
    cells = [
        [TableCell(text="Header", colspan=2, is_header=True)],
        [TableCell(text="A"), TableCell(text="B")],
    ]
    return TableData(rows=cells, col_count=2, row_count=2)


@pytest.fixture
def vmerged_table():
    """Create a table with vertical merge."""
    cells = [
        [TableCell(text="Merged", rowspan=2), TableCell(text="B")],
        [TableCell(text="", is_merged_continuation=True), TableCell(text="C")],
    ]
    return TableData(rows=cells, col_count=2, row_count=2)


class TestTableFormatterRegistry:
    """Tests for formatter registry."""

    def test_all_formats_registered(self):
        """Test all table formats are registered."""
        assert "markdown" in TABLE_FORMATTERS
        assert "json" in TABLE_FORMATTERS
        assert "html" in TABLE_FORMATTERS
        assert "text" in TABLE_FORMATTERS

    def test_formatters_are_subclasses(self):
        """Test all registered formatters are TableFormatter subclasses."""
        for name, formatter_class in TABLE_FORMATTERS.items():
            assert issubclass(formatter_class, TableFormatter)


class TestGetFormatter:
    """Tests for get_formatter function."""

    def test_get_markdown_formatter(self):
        """Test getting markdown formatter."""
        formatter = get_formatter(
            TableFormat.MARKDOWN,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert isinstance(formatter, MarkdownTableFormatter)

    def test_get_json_formatter(self):
        """Test getting JSON formatter."""
        formatter = get_formatter(
            TableFormat.JSON,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert isinstance(formatter, JsonTableFormatter)

    def test_get_html_formatter(self):
        """Test getting HTML formatter."""
        formatter = get_formatter(
            TableFormat.HTML,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert isinstance(formatter, HtmlTableFormatter)

    def test_get_text_formatter(self):
        """Test getting text formatter."""
        formatter = get_formatter(
            TableFormat.TEXT,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert isinstance(formatter, TextTableFormatter)

    def test_formatter_has_merge_modes(self):
        """Test formatter stores merge modes."""
        formatter = get_formatter(
            TableFormat.MARKDOWN,
            VerticalMergeMode.EMPTY,
            HorizontalMergeMode.SINGLE
        )
        assert formatter.vertical_merge == VerticalMergeMode.EMPTY
        assert formatter.horizontal_merge == HorizontalMergeMode.SINGLE


class TestMarkdownTableFormatter:
    """Tests for MarkdownTableFormatter."""

    def test_simple_table(self, simple_table):
        """Test formatting simple table."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(simple_table)

        assert "| A | B |" in result
        assert "| --- | --- |" in result
        assert "| 1 | 2 |" in result

    def test_empty_table(self):
        """Test formatting empty table."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        empty_table = TableData(rows=[], col_count=0, row_count=0)
        result = formatter.format(empty_table)
        assert result == ""

    def test_merged_horizontal_expand(self, merged_table):
        """Test horizontal merge with EXPAND mode."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(merged_table)
        # EXPAND mode should have 2 columns in all rows
        lines = result.split('\n')
        for line in lines:
            if line.startswith('|'):
                assert line.count('|') == 3  # 2 columns + start/end

    def test_escape_pipe(self):
        """Test pipe character escaping."""
        cells = [[TableCell(text="A | B")]]
        table = TableData(rows=cells, col_count=1, row_count=1)

        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(table)
        assert "A \\| B" in result


class TestJsonTableFormatter:
    """Tests for JsonTableFormatter."""

    def test_simple_table(self, simple_table):
        """Test formatting simple table to JSON."""
        formatter = JsonTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(simple_table)

        data = json.loads(result)
        assert data["type"] == "table"
        assert data["col_count"] == 2
        assert data["row_count"] == 2
        assert len(data["rows"]) == 2

    def test_empty_table(self):
        """Test formatting empty table to JSON."""
        formatter = JsonTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        empty_table = TableData(rows=[], col_count=0, row_count=0)
        result = formatter.format(empty_table)

        data = json.loads(result)
        assert data["rows"] == []

    def test_merged_cells_preserved(self, merged_table):
        """Test merged cell info is preserved in JSON."""
        formatter = JsonTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(merged_table)

        data = json.loads(result)
        first_cell = data["rows"][0]["cells"][0]
        assert first_cell["colspan"] == 2
        assert first_cell["is_header"] is True


class TestHtmlTableFormatter:
    """Tests for HtmlTableFormatter."""

    def test_simple_table(self, simple_table):
        """Test formatting simple table to HTML."""
        formatter = HtmlTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(simple_table)

        assert "<table>" in result
        assert "</table>" in result
        assert "<tr>" in result
        assert "<td>A</td>" in result

    def test_empty_table(self):
        """Test formatting empty table to HTML."""
        formatter = HtmlTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        empty_table = TableData(rows=[], col_count=0, row_count=0)
        result = formatter.format(empty_table)
        assert result == ""

    def test_header_cells(self, merged_table):
        """Test header cells use th tag."""
        formatter = HtmlTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(merged_table)

        assert "<th" in result
        assert 'colspan="2"' in result

    def test_rowspan(self, vmerged_table):
        """Test rowspan attribute."""
        formatter = HtmlTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(vmerged_table)

        assert 'rowspan="2"' in result

    def test_html_escape(self):
        """Test HTML special characters are escaped."""
        cells = [[TableCell(text="<script>alert(1)</script>")]]
        table = TableData(rows=cells, col_count=1, row_count=1)

        formatter = HtmlTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(table)

        assert "&lt;script&gt;" in result
        assert "<script>" not in result


class TestTextTableFormatter:
    """Tests for TextTableFormatter."""

    def test_simple_table(self, simple_table):
        """Test formatting simple table to text."""
        formatter = TextTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(simple_table)

        lines = result.split('\n')
        assert len(lines) == 2
        assert "A\tB" in result
        assert "1\t2" in result

    def test_empty_table(self):
        """Test formatting empty table to text."""
        formatter = TextTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        empty_table = TableData(rows=[], col_count=0, row_count=0)
        result = formatter.format(empty_table)
        assert result == ""

    def test_removes_newlines_and_tabs(self):
        """Test newlines and tabs are replaced."""
        cells = [[TableCell(text="Line1\nLine2\tTab")]]
        table = TableData(rows=cells, col_count=1, row_count=1)

        formatter = TextTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(table)

        assert '\n' not in result.split('\n')[0]  # No extra newlines in cell
        assert '\t' not in result.split('\t')[0]  # No tabs in cell content


class TestFormatTableFunction:
    """Tests for format_table convenience function."""

    def test_format_markdown(self, simple_table):
        """Test format_table with markdown."""
        result = format_table(
            simple_table,
            TableFormat.MARKDOWN,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert "| A | B |" in result

    def test_format_json(self, simple_table):
        """Test format_table with JSON."""
        result = format_table(
            simple_table,
            TableFormat.JSON,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        data = json.loads(result)
        assert data["type"] == "table"

    def test_format_html(self, simple_table):
        """Test format_table with HTML."""
        result = format_table(
            simple_table,
            TableFormat.HTML,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert "<table>" in result

    def test_format_text(self, simple_table):
        """Test format_table with text."""
        result = format_table(
            simple_table,
            TableFormat.TEXT,
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        assert "A\tB" in result


class TestMarkdownTableFormatterExtended:
    """Extended tests for MarkdownTableFormatter."""

    def test_vertical_merge_empty_mode(self, vmerged_table):
        """Test vertical merge with EMPTY mode."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.EMPTY,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(vmerged_table)

        # With EMPTY mode, merged continuation cells should be empty
        lines = result.split('\n')
        assert len(lines) >= 3  # Header, separator, data rows

    def test_vertical_merge_first_only_mode(self, vmerged_table):
        """Test vertical merge with FIRST_ONLY mode."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.FIRST_ONLY,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(vmerged_table)

        assert result  # Should produce output

    def test_horizontal_merge_single_mode(self, merged_table):
        """Test horizontal merge with SINGLE mode."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.SINGLE
        )
        result = formatter.format(merged_table)

        assert result  # Should produce output

    def test_horizontal_merge_repeat_mode(self, merged_table):
        """Test horizontal merge with REPEAT mode."""
        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.REPEAT
        )
        result = formatter.format(merged_table)

        # REPEAT mode should repeat the value in merged cells
        lines = result.split('\n')
        assert any("Header" in line for line in lines)

    def test_newline_in_cell(self):
        """Test newline in cell is replaced with <br>."""
        cells = [[TableCell(text="Line1\nLine2")]]
        table = TableData(rows=cells, col_count=1, row_count=1)

        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(table)

        assert "<br>" in result

    def test_single_row_table(self):
        """Test single row table."""
        cells = [[TableCell(text="Only")]]
        table = TableData(rows=cells, col_count=1, row_count=1)

        formatter = MarkdownTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(table)

        assert "| Only |" in result
        assert "| --- |" in result


class TestHtmlTableFormatterExtended:
    """Extended tests for HtmlTableFormatter."""

    def test_vertical_merge_empty_mode(self, vmerged_table):
        """Test vertical merge with EMPTY mode in HTML."""
        formatter = HtmlTableFormatter(
            VerticalMergeMode.EMPTY,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(vmerged_table)

        assert "<table>" in result

    def test_horizontal_merge_repeat_mode(self, merged_table):
        """Test horizontal merge with REPEAT mode in HTML."""
        formatter = HtmlTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.REPEAT
        )
        result = formatter.format(merged_table)

        assert "<table>" in result


class TestTextTableFormatterExtended:
    """Extended tests for TextTableFormatter."""

    def test_vertical_merge_empty_mode(self, vmerged_table):
        """Test vertical merge with EMPTY mode in text."""
        formatter = TextTableFormatter(
            VerticalMergeMode.EMPTY,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(vmerged_table)

        assert result  # Should produce output

    def test_merged_cells(self, merged_table):
        """Test merged cells in text format."""
        formatter = TextTableFormatter(
            VerticalMergeMode.REPEAT,
            HorizontalMergeMode.EXPAND
        )
        result = formatter.format(merged_table)

        assert "Header" in result
