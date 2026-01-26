"""Configuration classes for docx-parser.

This module provides configuration dataclasses to group related parameters,
improving code readability and reducing the number of function arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


# =============================================================================
# Enum Types (will be moved to models/enums.py in Phase 1)
# =============================================================================

class VerticalMergeMode(Enum):
    """How to handle vertically merged cells in tables.

    Attributes:
        REPEAT: Repeat the merged cell content in each row.
        EMPTY: Leave merged cells empty (default Word behavior).
        FIRST_ONLY: Only show content in the first cell of the merge.
    """
    REPEAT = "repeat"
    EMPTY = "empty"
    FIRST_ONLY = "first_only"


class HorizontalMergeMode(Enum):
    """How to handle horizontally merged cells in tables.

    Attributes:
        EXPAND: Expand content across merged columns.
        SINGLE: Show content only in the first merged cell.
        REPEAT: Repeat content in each merged cell.
    """
    EXPAND = "expand"
    SINGLE = "single"
    REPEAT = "repeat"


class OutputFormat(Enum):
    """Output format for parsed content.

    Attributes:
        MARKDOWN: Markdown format with headers, tables, and image placeholders.
        TEXT: Plain text without formatting.
        JSON: Structured JSON with block-level elements.
    """
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


class HierarchyMode(Enum):
    """Mode for detecting heading hierarchy.

    Attributes:
        NONE: No hierarchy detection; all text is treated as paragraphs.
        AUTO: Automatically detect using style first, then font size.
        STYLE: Use Word heading styles (Heading 1, Heading 2, etc.).
        FONT_SIZE: Use font size to determine heading levels.
        PATTERN: Use custom regex patterns for heading detection.
    """
    NONE = "none"
    AUTO = "auto"
    STYLE = "style"
    FONT_SIZE = "font_size"
    PATTERN = "pattern"


class TableFormat(Enum):
    """Output format for tables.

    Attributes:
        MARKDOWN: Markdown table syntax.
        JSON: JSON array of row objects.
        HTML: HTML table markup.
        TEXT: Plain text with column separators.
    """
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"


# =============================================================================
# Type Aliases
# =============================================================================

# Pattern for heading detection: (level, pattern_string)
HeadingPattern = Tuple[int, str]


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class ImageConfig:
    """Configuration for image extraction and processing.

    Attributes:
        extract: Whether to extract images from the document.
        convert_to_png: Whether to convert non-standard formats to PNG.
        output_dir: Directory to save extracted images.
    """
    extract: bool = True
    convert_to_png: bool = True
    output_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.output_dir is not None and isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)


@dataclass
class TableConfig:
    """Configuration for table parsing.

    Attributes:
        format: Output format for tables.
        vertical_merge: How to handle vertically merged cells.
        horizontal_merge: How to handle horizontally merged cells.
        include_empty: Whether to include empty tables.
    """
    format: TableFormat = TableFormat.MARKDOWN
    vertical_merge: VerticalMergeMode = VerticalMergeMode.REPEAT
    horizontal_merge: HorizontalMergeMode = HorizontalMergeMode.EXPAND
    include_empty: bool = False


@dataclass
class HierarchyConfig:
    """Configuration for heading hierarchy detection.

    Attributes:
        mode: The hierarchy detection mode.
        max_level: Maximum heading level to detect (1-6).
        custom_patterns: Custom regex patterns for PATTERN mode.
            Format: [(level, pattern), ...] e.g., [(1, "^I\\. "), (2, "^\\d+\\. ")]
    """
    mode: HierarchyMode = HierarchyMode.NONE
    max_level: int = 6
    custom_patterns: Optional[List[HeadingPattern]] = None

    def __post_init__(self) -> None:
        # Clamp max_level between 1 and 6
        self.max_level = max(1, min(6, self.max_level))


@dataclass
class MetadataConfig:
    """Configuration for metadata extraction.

    Attributes:
        extract: Whether to extract document metadata.
        include_custom: Whether to include custom properties.
    """
    extract: bool = True
    include_custom: bool = False


@dataclass
class ParseConfig:
    """Main configuration for DocxParser.

    This dataclass groups all parsing configuration options, replacing
    the 17+ individual parameters previously passed to parse_docx().

    Attributes:
        output_format: The format for parsed content output.
        image: Image extraction and processing configuration.
        table: Table parsing configuration.
        hierarchy: Heading hierarchy detection configuration.
        metadata: Metadata extraction configuration.

    Example:
        >>> config = ParseConfig(
        ...     output_format=OutputFormat.MARKDOWN,
        ...     image=ImageConfig(extract=True, convert_to_png=True),
        ...     table=TableConfig(format=TableFormat.MARKDOWN),
        ...     hierarchy=HierarchyConfig(mode=HierarchyMode.AUTO),
        ... )
        >>> result = parser.parse("document.docx", config=config)
    """
    output_format: OutputFormat = OutputFormat.MARKDOWN
    image: ImageConfig = field(default_factory=ImageConfig)
    table: TableConfig = field(default_factory=TableConfig)
    hierarchy: HierarchyConfig = field(default_factory=HierarchyConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)

    @classmethod
    def from_kwargs(cls, **kwargs) -> "ParseConfig":
        """Create ParseConfig from flat keyword arguments.

        This method provides backward compatibility with the old
        parse_docx() signature that used flat parameters.

        Args:
            **kwargs: Flat keyword arguments matching old parameter names.

        Returns:
            ParseConfig: A new configuration instance.

        Example:
            >>> config = ParseConfig.from_kwargs(
            ...     extract_images=True,
            ...     output_format="markdown",
            ...     vertical_merge="repeat",
            ... )
        """
        # Map old parameter names to new structure
        image_config = ImageConfig(
            extract=kwargs.get("extract_images", True),
            convert_to_png=kwargs.get("convert_images_to_png", True),
            output_dir=kwargs.get("output_dir"),
        )

        # Handle enum conversion from string
        table_format = kwargs.get("table_format", TableFormat.MARKDOWN)
        if isinstance(table_format, str):
            table_format = TableFormat(table_format)

        vertical_merge = kwargs.get("vertical_merge", VerticalMergeMode.REPEAT)
        if isinstance(vertical_merge, str):
            vertical_merge = VerticalMergeMode(vertical_merge)

        horizontal_merge = kwargs.get("horizontal_merge", HorizontalMergeMode.EXPAND)
        if isinstance(horizontal_merge, str):
            horizontal_merge = HorizontalMergeMode(horizontal_merge)

        table_config = TableConfig(
            format=table_format,
            vertical_merge=vertical_merge,
            horizontal_merge=horizontal_merge,
        )

        hierarchy_mode = kwargs.get("hierarchy_mode", HierarchyMode.NONE)
        if isinstance(hierarchy_mode, str):
            hierarchy_mode = HierarchyMode(hierarchy_mode)

        hierarchy_config = HierarchyConfig(
            mode=hierarchy_mode,
            max_level=kwargs.get("max_heading_level", 6),
            custom_patterns=kwargs.get("heading_patterns"),
        )

        metadata_config = MetadataConfig(
            extract=kwargs.get("extract_metadata", True),
        )

        output_format = kwargs.get("output_format", OutputFormat.MARKDOWN)
        if isinstance(output_format, str):
            output_format = OutputFormat(output_format)

        return cls(
            output_format=output_format,
            image=image_config,
            table=table_config,
            hierarchy=hierarchy_config,
            metadata=metadata_config,
        )

    def to_dict(self) -> Dict[str, Union[str, bool, int, None]]:
        """Convert configuration to a flat dictionary.

        Returns:
            Dict with all configuration values.
        """
        return {
            "output_format": self.output_format.value,
            "extract_images": self.image.extract,
            "convert_images_to_png": self.image.convert_to_png,
            "output_dir": str(self.image.output_dir) if self.image.output_dir else None,
            "table_format": self.table.format.value,
            "vertical_merge": self.table.vertical_merge.value,
            "horizontal_merge": self.table.horizontal_merge.value,
            "hierarchy_mode": self.hierarchy.mode.value,
            "max_heading_level": self.hierarchy.max_level,
            "extract_metadata": self.metadata.extract,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "VerticalMergeMode",
    "HorizontalMergeMode",
    "OutputFormat",
    "HierarchyMode",
    "TableFormat",
    # Type aliases
    "HeadingPattern",
    # Config classes
    "ImageConfig",
    "TableConfig",
    "HierarchyConfig",
    "MetadataConfig",
    "ParseConfig",
]
