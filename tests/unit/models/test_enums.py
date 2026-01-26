"""Tests for docx_parser.models.enums module."""

import pytest

from docx_parser.models.enums import (
    BlockType,
    HeadingPattern,
    HierarchyMode,
    HorizontalMergeMode,
    OutputFormat,
    TableFormat,
    VerticalMergeMode,
)


class TestVerticalMergeMode:
    """Tests for VerticalMergeMode enum."""

    def test_values(self):
        """Test all enum values exist."""
        assert VerticalMergeMode.REPEAT.value == "repeat"
        assert VerticalMergeMode.EMPTY.value == "empty"
        assert VerticalMergeMode.FIRST_ONLY.value == "first"

    def test_str_enum(self):
        """Test that enum is also a string."""
        assert isinstance(VerticalMergeMode.REPEAT, str)
        # str(enum) includes class name, but value is accessible
        assert VerticalMergeMode.REPEAT.value == "repeat"

    def test_from_string(self):
        """Test creating enum from string."""
        assert VerticalMergeMode("repeat") == VerticalMergeMode.REPEAT
        assert VerticalMergeMode("empty") == VerticalMergeMode.EMPTY
        assert VerticalMergeMode("first") == VerticalMergeMode.FIRST_ONLY

    def test_invalid_value_raises(self):
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            VerticalMergeMode("invalid")


class TestHorizontalMergeMode:
    """Tests for HorizontalMergeMode enum."""

    def test_values(self):
        """Test all enum values exist."""
        assert HorizontalMergeMode.EXPAND.value == "expand"
        assert HorizontalMergeMode.SINGLE.value == "single"
        assert HorizontalMergeMode.REPEAT.value == "repeat"

    def test_str_enum(self):
        """Test that enum is also a string."""
        assert isinstance(HorizontalMergeMode.EXPAND, str)
        assert HorizontalMergeMode.SINGLE.value == "single"


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_values(self):
        """Test all enum values exist."""
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.JSON.value == "json"

    def test_default_is_markdown(self):
        """Test that markdown is the intended default."""
        assert OutputFormat.MARKDOWN == OutputFormat("markdown")

    def test_str_enum(self):
        """Test that enum is also a string."""
        assert isinstance(OutputFormat.MARKDOWN, str)


class TestHierarchyMode:
    """Tests for HierarchyMode enum."""

    def test_values(self):
        """Test all enum values exist."""
        assert HierarchyMode.NONE.value == "none"
        assert HierarchyMode.AUTO.value == "auto"
        assert HierarchyMode.STYLE.value == "style"
        assert HierarchyMode.FONT_SIZE.value == "font_size"
        assert HierarchyMode.PATTERN.value == "pattern"

    def test_default_is_none(self):
        """Test that NONE is the backward compatible default."""
        assert HierarchyMode.NONE == HierarchyMode("none")

    def test_all_modes_count(self):
        """Test that all expected modes are present."""
        assert len(HierarchyMode) == 5


class TestTableFormat:
    """Tests for TableFormat enum."""

    def test_values(self):
        """Test all enum values exist."""
        assert TableFormat.MARKDOWN.value == "markdown"
        assert TableFormat.JSON.value == "json"
        assert TableFormat.HTML.value == "html"
        assert TableFormat.TEXT.value == "text"

    def test_all_formats_count(self):
        """Test that all expected formats are present."""
        assert len(TableFormat) == 4


class TestBlockType:
    """Tests for BlockType enum."""

    def test_values(self):
        """Test all enum values exist."""
        assert BlockType.PARAGRAPH.value == "paragraph"
        assert BlockType.HEADING.value == "heading"
        assert BlockType.TABLE.value == "table"
        assert BlockType.IMAGE.value == "image"

    def test_all_types_count(self):
        """Test that all expected types are present."""
        assert len(BlockType) == 4


class TestHeadingPattern:
    """Tests for HeadingPattern type alias."""

    def test_type_alias_accepts_valid_list(self):
        """Test that HeadingPattern accepts valid list structure."""
        patterns: HeadingPattern = [
            ("I. ", 1),
            ("1. ", 2),
            ("1)", 3),
        ]
        assert len(patterns) == 3
        assert patterns[0] == ("I. ", 1)

    def test_empty_list_is_valid(self):
        """Test that empty list is a valid HeadingPattern."""
        patterns: HeadingPattern = []
        assert patterns == []
