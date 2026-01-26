"""Tests for docx_parser.models.image module."""

import pytest

from docx_parser.models.image import ImageInfo, StyleInfo


class TestImageInfo:
    """Tests for ImageInfo dataclass."""

    def test_minimal_creation(self):
        """Test creating ImageInfo with minimal required fields."""
        info = ImageInfo(index=1, name="001_image.png")
        assert info.index == 1
        assert info.name == "001_image.png"
        assert info.path is None
        assert info.original_name is None
        assert info.data is None

    def test_full_creation(self):
        """Test creating ImageInfo with all fields."""
        info = ImageInfo(
            index=1,
            name="001_logo.png",
            path="/output/001_logo.png",
            original_name="image1.png",
            data=b"\x89PNG"
        )
        assert info.index == 1
        assert info.name == "001_logo.png"
        assert info.path == "/output/001_logo.png"
        assert info.original_name == "image1.png"
        assert info.data == b"\x89PNG"

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        info = ImageInfo(index=1, name="001_image.png")
        result = info.to_dict()

        assert result == {
            "index": 1,
            "name": "001_image.png",
            "path": None,
            "original_name": None
        }

    def test_to_dict_excludes_data(self):
        """Test that to_dict excludes binary data field."""
        info = ImageInfo(
            index=1,
            name="001_image.png",
            data=b"\x89PNG\r\n\x1a\n" * 1000
        )
        result = info.to_dict()

        assert "data" not in result

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        info = ImageInfo(
            index=5,
            name="005_chart.png",
            path="/images/005_chart.png",
            original_name="sales_chart.png",
            data=b"test"
        )
        result = info.to_dict()

        assert result == {
            "index": 5,
            "name": "005_chart.png",
            "path": "/images/005_chart.png",
            "original_name": "sales_chart.png"
        }

    def test_index_zero_is_valid(self):
        """Test that index 0 is valid (though typically 1-based)."""
        info = ImageInfo(index=0, name="000_image.png")
        assert info.index == 0

    def test_negative_index(self):
        """Test that negative index doesn't raise (dataclass doesn't validate)."""
        info = ImageInfo(index=-1, name="test.png")
        assert info.index == -1

    def test_empty_name(self):
        """Test that empty name is allowed by dataclass."""
        info = ImageInfo(index=1, name="")
        assert info.name == ""


class TestStyleInfo:
    """Tests for StyleInfo dataclass."""

    def test_minimal_creation(self):
        """Test creating StyleInfo with minimal required fields."""
        style = StyleInfo(style_id="Heading1")
        assert style.style_id == "Heading1"
        assert style.name is None
        assert style.outline_level is None
        assert style.font_size is None

    def test_full_creation(self):
        """Test creating StyleInfo with all fields."""
        style = StyleInfo(
            style_id="Heading1",
            name="Heading 1",
            outline_level=0,
            font_size=32
        )
        assert style.style_id == "Heading1"
        assert style.name == "Heading 1"
        assert style.outline_level == 0
        assert style.font_size == 32

    def test_outline_level_h1(self):
        """Test outline_level 0 represents H1."""
        style = StyleInfo(style_id="H1", outline_level=0)
        assert style.outline_level == 0  # H1

    def test_outline_level_h9(self):
        """Test outline_level 8 represents H9."""
        style = StyleInfo(style_id="H9", outline_level=8)
        assert style.outline_level == 8  # H9

    def test_font_size_in_half_points(self):
        """Test font_size is stored in half-points (24 = 12pt)."""
        style = StyleInfo(style_id="Normal", font_size=24)
        # 24 half-points = 12pt
        assert style.font_size == 24
        assert style.font_size / 2 == 12  # Convert to points

    def test_style_id_with_spaces(self):
        """Test style_id with spaces is valid."""
        style = StyleInfo(style_id="List Paragraph")
        assert style.style_id == "List Paragraph"

    def test_empty_style_id(self):
        """Test that empty style_id is allowed."""
        style = StyleInfo(style_id="")
        assert style.style_id == ""

    def test_unicode_name(self):
        """Test Korean/Unicode style name."""
        style = StyleInfo(style_id="CustomStyle", name="제목 1")
        assert style.name == "제목 1"
