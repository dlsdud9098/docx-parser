"""Tests for docx_parser.models.blocks module."""

import pytest

from docx_parser.models.blocks import (
    HeadingBlock,
    ImageBlock,
    ParagraphBlock,
    TableBlock,
)
from docx_parser.models.enums import BlockType


class TestParagraphBlock:
    """Tests for ParagraphBlock dataclass."""

    def test_creation(self):
        """Test creating ParagraphBlock."""
        block = ParagraphBlock(content="Hello world")
        assert block.content == "Hello world"

    def test_empty_content(self):
        """Test creating ParagraphBlock with empty content."""
        block = ParagraphBlock(content="")
        assert block.content == ""

    def test_to_dict(self):
        """Test to_dict method."""
        block = ParagraphBlock(content="Test paragraph")
        result = block.to_dict()

        assert result == {
            "type": BlockType.PARAGRAPH.value,
            "content": "Test paragraph"
        }

    def test_to_dict_type_is_string(self):
        """Test that type in to_dict is string, not enum."""
        block = ParagraphBlock(content="Test")
        result = block.to_dict()

        assert result["type"] == "paragraph"
        assert isinstance(result["type"], str)

    def test_multiline_content(self):
        """Test with multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        block = ParagraphBlock(content=content)
        assert block.content == content
        assert block.to_dict()["content"] == content

    def test_unicode_content(self):
        """Test with Korean/Unicode content."""
        block = ParagraphBlock(content="안녕하세요 세계")
        assert block.content == "안녕하세요 세계"


class TestHeadingBlock:
    """Tests for HeadingBlock dataclass."""

    def test_creation(self):
        """Test creating HeadingBlock."""
        block = HeadingBlock(content="Introduction", level=1)
        assert block.content == "Introduction"
        assert block.level == 1

    def test_level_range(self):
        """Test heading levels 1-6."""
        for level in range(1, 7):
            block = HeadingBlock(content=f"Heading {level}", level=level)
            assert block.level == level

    def test_to_dict(self):
        """Test to_dict method."""
        block = HeadingBlock(content="Chapter 1", level=2)
        result = block.to_dict()

        assert result == {
            "type": BlockType.HEADING.value,
            "level": 2,
            "content": "Chapter 1"
        }

    def test_to_dict_type_is_string(self):
        """Test that type in to_dict is string."""
        block = HeadingBlock(content="Title", level=1)
        result = block.to_dict()

        assert result["type"] == "heading"

    def test_level_zero(self):
        """Test level 0 is allowed (dataclass doesn't validate)."""
        block = HeadingBlock(content="Zero", level=0)
        assert block.level == 0


class TestTableBlock:
    """Tests for TableBlock dataclass."""

    def test_minimal_creation(self):
        """Test creating TableBlock with minimal fields."""
        rows = [["A", "B"], ["1", "2"]]
        block = TableBlock(rows=rows)

        assert block.rows == rows
        assert block.headers is None
        assert block.metadata is None

    def test_with_headers(self):
        """Test creating TableBlock with headers."""
        block = TableBlock(
            rows=[["1", "2"], ["3", "4"]],
            headers=["Col1", "Col2"]
        )
        assert block.headers == ["Col1", "Col2"]

    def test_with_metadata(self):
        """Test creating TableBlock with metadata."""
        block = TableBlock(
            rows=[["A", "B"]],
            metadata={"caption": "Table 1"}
        )
        assert block.metadata == {"caption": "Table 1"}

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        block = TableBlock(rows=[["A", "B"]])
        result = block.to_dict()

        assert result == {
            "type": "table",
            "rows": [["A", "B"]]
        }
        assert "headers" not in result
        assert "metadata" not in result

    def test_to_dict_with_headers(self):
        """Test to_dict with headers."""
        block = TableBlock(
            rows=[["1", "2"]],
            headers=["X", "Y"]
        )
        result = block.to_dict()

        assert result == {
            "type": "table",
            "rows": [["1", "2"]],
            "headers": ["X", "Y"]
        }

    def test_to_dict_with_metadata(self):
        """Test to_dict with metadata."""
        block = TableBlock(
            rows=[["A"]],
            metadata={"key": "value"}
        )
        result = block.to_dict()

        assert result["metadata"] == {"key": "value"}

    def test_empty_rows(self):
        """Test with empty rows list."""
        block = TableBlock(rows=[])
        assert block.rows == []
        assert block.to_dict()["rows"] == []

    def test_unicode_content(self):
        """Test with Korean/Unicode content."""
        block = TableBlock(
            rows=[["이름", "나이"], ["홍길동", "30"]],
            headers=["항목1", "항목2"]
        )
        assert block.rows[1][0] == "홍길동"


class TestImageBlock:
    """Tests for ImageBlock dataclass."""

    def test_minimal_creation(self):
        """Test creating ImageBlock with minimal fields."""
        block = ImageBlock(index=1)
        assert block.index == 1
        assert block.path is None
        assert block.description is None

    def test_full_creation(self):
        """Test creating ImageBlock with all fields."""
        block = ImageBlock(
            index=5,
            path="/images/005.png",
            description="Company logo"
        )
        assert block.index == 5
        assert block.path == "/images/005.png"
        assert block.description == "Company logo"

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        block = ImageBlock(index=1)
        result = block.to_dict()

        assert result == {
            "type": "image",
            "index": 1
        }
        assert "path" not in result
        assert "description" not in result

    def test_to_dict_with_path(self):
        """Test to_dict with path."""
        block = ImageBlock(index=1, path="/img/001.png")
        result = block.to_dict()

        assert result["path"] == "/img/001.png"

    def test_to_dict_with_description(self):
        """Test to_dict with description."""
        block = ImageBlock(index=1, description="A chart showing sales")
        result = block.to_dict()

        assert result["description"] == "A chart showing sales"

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        block = ImageBlock(
            index=3,
            path="/output/003.png",
            description="Technical diagram"
        )
        result = block.to_dict()

        assert result == {
            "type": "image",
            "index": 3,
            "path": "/output/003.png",
            "description": "Technical diagram"
        }

    def test_index_zero(self):
        """Test index 0 is allowed."""
        block = ImageBlock(index=0)
        assert block.index == 0
