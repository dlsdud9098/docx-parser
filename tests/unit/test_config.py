"""Unit tests for docx_parser.config module.

Tests configuration dataclasses and enum types.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from docx_parser.config import (
    # Enums
    VerticalMergeMode,
    HorizontalMergeMode,
    OutputFormat,
    HierarchyMode,
    TableFormat,
    # Config classes
    ImageConfig,
    TableConfig,
    HierarchyConfig,
    MetadataConfig,
    ParseConfig,
)


class TestVerticalMergeMode:
    """Tests for VerticalMergeMode enum."""

    def test_values(self) -> None:
        """Test all enum values exist."""
        assert VerticalMergeMode.REPEAT.value == "repeat"
        assert VerticalMergeMode.EMPTY.value == "empty"
        assert VerticalMergeMode.FIRST_ONLY.value == "first_only"

    def test_from_string(self) -> None:
        """Test creating enum from string."""
        assert VerticalMergeMode("repeat") == VerticalMergeMode.REPEAT
        assert VerticalMergeMode("empty") == VerticalMergeMode.EMPTY


class TestHorizontalMergeMode:
    """Tests for HorizontalMergeMode enum."""

    def test_values(self) -> None:
        """Test all enum values exist."""
        assert HorizontalMergeMode.EXPAND.value == "expand"
        assert HorizontalMergeMode.SINGLE.value == "single"
        assert HorizontalMergeMode.REPEAT.value == "repeat"


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_values(self) -> None:
        """Test all enum values exist."""
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.JSON.value == "json"


class TestHierarchyMode:
    """Tests for HierarchyMode enum."""

    def test_values(self) -> None:
        """Test all enum values exist."""
        assert HierarchyMode.NONE.value == "none"
        assert HierarchyMode.AUTO.value == "auto"
        assert HierarchyMode.STYLE.value == "style"
        assert HierarchyMode.FONT_SIZE.value == "font_size"
        assert HierarchyMode.PATTERN.value == "pattern"


class TestTableFormat:
    """Tests for TableFormat enum."""

    def test_values(self) -> None:
        """Test all enum values exist."""
        assert TableFormat.MARKDOWN.value == "markdown"
        assert TableFormat.JSON.value == "json"
        assert TableFormat.HTML.value == "html"
        assert TableFormat.TEXT.value == "text"


class TestImageConfig:
    """Tests for ImageConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ImageConfig()
        assert config.extract is True
        assert config.convert_to_png is True
        assert config.output_dir is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ImageConfig(
            extract=False,
            convert_to_png=False,
            output_dir=Path("/output")
        )
        assert config.extract is False
        assert config.convert_to_png is False
        assert config.output_dir == Path("/output")

    def test_string_path_conversion(self) -> None:
        """Test string path is converted to Path."""
        config = ImageConfig(output_dir="/output")
        assert isinstance(config.output_dir, Path)
        assert config.output_dir == Path("/output")


class TestTableConfig:
    """Tests for TableConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = TableConfig()
        assert config.format == TableFormat.MARKDOWN
        assert config.vertical_merge == VerticalMergeMode.REPEAT
        assert config.horizontal_merge == HorizontalMergeMode.EXPAND
        assert config.include_empty is False

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = TableConfig(
            format=TableFormat.JSON,
            vertical_merge=VerticalMergeMode.EMPTY,
            horizontal_merge=HorizontalMergeMode.SINGLE,
            include_empty=True
        )
        assert config.format == TableFormat.JSON
        assert config.vertical_merge == VerticalMergeMode.EMPTY
        assert config.horizontal_merge == HorizontalMergeMode.SINGLE
        assert config.include_empty is True


class TestHierarchyConfig:
    """Tests for HierarchyConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = HierarchyConfig()
        assert config.mode == HierarchyMode.NONE
        assert config.max_level == 6
        assert config.custom_patterns is None

    def test_max_level_clamping_low(self) -> None:
        """Test max_level is clamped to minimum 1."""
        config = HierarchyConfig(max_level=0)
        assert config.max_level == 1

    def test_max_level_clamping_high(self) -> None:
        """Test max_level is clamped to maximum 6."""
        config = HierarchyConfig(max_level=10)
        assert config.max_level == 6

    def test_custom_patterns(self) -> None:
        """Test custom heading patterns."""
        patterns = [(1, r"^I\. "), (2, r"^\d+\. ")]
        config = HierarchyConfig(
            mode=HierarchyMode.PATTERN,
            custom_patterns=patterns
        )
        assert config.custom_patterns == patterns


class TestMetadataConfig:
    """Tests for MetadataConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MetadataConfig()
        assert config.extract is True
        assert config.include_custom is False


class TestParseConfig:
    """Tests for ParseConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ParseConfig()
        assert config.output_format == OutputFormat.MARKDOWN
        assert isinstance(config.image, ImageConfig)
        assert isinstance(config.table, TableConfig)
        assert isinstance(config.hierarchy, HierarchyConfig)
        assert isinstance(config.metadata, MetadataConfig)

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ParseConfig(
            output_format=OutputFormat.JSON,
            image=ImageConfig(extract=False),
            table=TableConfig(format=TableFormat.HTML),
        )
        assert config.output_format == OutputFormat.JSON
        assert config.image.extract is False
        assert config.table.format == TableFormat.HTML

    def test_from_kwargs_basic(self) -> None:
        """Test from_kwargs with basic parameters."""
        config = ParseConfig.from_kwargs(
            extract_images=False,
            output_format="json",
        )
        assert config.image.extract is False
        assert config.output_format == OutputFormat.JSON

    def test_from_kwargs_all_parameters(self) -> None:
        """Test from_kwargs with all parameters."""
        config = ParseConfig.from_kwargs(
            extract_images=True,
            convert_images_to_png=False,
            output_dir="/output",
            output_format="text",
            table_format="html",
            vertical_merge="empty",
            horizontal_merge="single",
            hierarchy_mode="auto",
            max_heading_level=4,
            extract_metadata=False,
        )
        assert config.image.extract is True
        assert config.image.convert_to_png is False
        assert config.image.output_dir == Path("/output")
        assert config.output_format == OutputFormat.TEXT
        assert config.table.format == TableFormat.HTML
        assert config.table.vertical_merge == VerticalMergeMode.EMPTY
        assert config.table.horizontal_merge == HorizontalMergeMode.SINGLE
        assert config.hierarchy.mode == HierarchyMode.AUTO
        assert config.hierarchy.max_level == 4
        assert config.metadata.extract is False

    def test_from_kwargs_with_enum_values(self) -> None:
        """Test from_kwargs with enum values instead of strings."""
        config = ParseConfig.from_kwargs(
            output_format=OutputFormat.JSON,
            table_format=TableFormat.HTML,
        )
        assert config.output_format == OutputFormat.JSON
        assert config.table.format == TableFormat.HTML

    def test_to_dict(self) -> None:
        """Test to_dict returns flat dictionary."""
        config = ParseConfig(
            output_format=OutputFormat.JSON,
            image=ImageConfig(output_dir=Path("/output")),
        )
        result = config.to_dict()

        assert result["output_format"] == "json"
        assert result["extract_images"] is True
        assert result["output_dir"] == "/output"
        assert result["table_format"] == "markdown"

    def test_to_dict_none_output_dir(self) -> None:
        """Test to_dict with None output_dir."""
        config = ParseConfig()
        result = config.to_dict()
        assert result["output_dir"] is None


class TestEnumStringConversion:
    """Tests for enum string conversion in configs."""

    @pytest.mark.parametrize("value,expected", [
        ("markdown", OutputFormat.MARKDOWN),
        ("text", OutputFormat.TEXT),
        ("json", OutputFormat.JSON),
    ])
    def test_output_format_from_string(self, value: str, expected: OutputFormat) -> None:
        """Test OutputFormat from string conversion."""
        assert OutputFormat(value) == expected

    @pytest.mark.parametrize("value,expected", [
        ("repeat", VerticalMergeMode.REPEAT),
        ("empty", VerticalMergeMode.EMPTY),
        ("first_only", VerticalMergeMode.FIRST_ONLY),
    ])
    def test_vertical_merge_from_string(self, value: str, expected: VerticalMergeMode) -> None:
        """Test VerticalMergeMode from string conversion."""
        assert VerticalMergeMode(value) == expected

    def test_invalid_enum_value_raises(self) -> None:
        """Test invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            OutputFormat("invalid")
