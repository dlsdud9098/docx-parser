"""
Content block models for docx_parser.

This module contains block dataclasses for structured JSON output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .enums import BlockType


@dataclass
class ParagraphBlock:
    """Paragraph content block.

    Attributes:
        content: Paragraph text content.

    Example:
        >>> block = ParagraphBlock(content="Hello world")
        >>> block.to_dict()
        {'type': 'paragraph', 'content': 'Hello world'}
    """
    content: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with type and content.
        """
        return {
            "type": BlockType.PARAGRAPH.value,
            "content": self.content
        }


@dataclass
class HeadingBlock:
    """Heading content block.

    Attributes:
        content: Heading text content.
        level: Heading level (1-6).

    Example:
        >>> block = HeadingBlock(content="Introduction", level=1)
        >>> block.to_dict()
        {'type': 'heading', 'level': 1, 'content': 'Introduction'}
    """
    content: str
    level: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with type, level, and content.
        """
        return {
            "type": BlockType.HEADING.value,
            "level": self.level,
            "content": self.content
        }


@dataclass
class TableBlock:
    """Table content block.

    Attributes:
        rows: List of rows, each row is a list of cell strings.
        headers: Optional header row.
        metadata: Optional additional metadata.

    Example:
        >>> block = TableBlock(rows=[["A", "B"], ["1", "2"]], headers=["Col1", "Col2"])
        >>> block.to_dict()
        {'type': 'table', 'rows': [['A', 'B'], ['1', '2']], 'headers': ['Col1', 'Col2']}
    """
    rows: List[List[str]]
    headers: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with type, rows, and optional headers/metadata.
        """
        result: Dict[str, Any] = {
            "type": BlockType.TABLE.value,
            "rows": self.rows
        }
        if self.headers:
            result["headers"] = self.headers
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class ImageBlock:
    """Image content block.

    Attributes:
        index: Image index number.
        path: Path to the image file.
        description: Optional image description.

    Example:
        >>> block = ImageBlock(index=1, path="/images/001.png", description="Logo")
        >>> block.to_dict()
        {'type': 'image', 'index': 1, 'path': '/images/001.png', 'description': 'Logo'}
    """
    index: int
    path: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with type, index, and optional path/description.
        """
        result: Dict[str, Any] = {
            "type": BlockType.IMAGE.value,
            "index": self.index
        }
        if self.path:
            result["path"] = self.path
        if self.description:
            result["description"] = self.description
        return result
