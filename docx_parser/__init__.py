"""
docx-parser: DOCX parser with image extraction, metadata, vision, and LangChain integration

Features:
- Text extraction with [IMAGE_N] placeholders
- DOCX metadata extraction (author, title, page count, etc.)
- Multiple output formats (markdown, text, json)
- Multimodal vision for image description (OpenAI, Anthropic, Google, Transformers)
- LangChain Document compatible
"""

from .parser import (
    DocxParser,
    parse_docx,
    ParseResult,
    VerticalMergeMode,
    HorizontalMergeMode,
    OutputFormat,
    HierarchyMode,
    TableFormat,
    DocxMetadata,
    CoreMetadata,
    AppMetadata,
    ImageInfo,
    StyleInfo,
    TableCell,
    TableData,
)

__version__ = "0.3.4"
__all__ = [
    # Main parser
    "DocxParser",
    "parse_docx",
    "ParseResult",
    # Enums
    "VerticalMergeMode",
    "HorizontalMergeMode",
    "OutputFormat",
    "HierarchyMode",
    "TableFormat",
    # Metadata classes
    "DocxMetadata",
    "CoreMetadata",
    "AppMetadata",
    "ImageInfo",
    "StyleInfo",
    # Table classes
    "TableCell",
    "TableData",
]

# LangChain loaders (optional import)
try:
    from .langchain_loader import DocxDirectLoader, DocxDirectoryLoader
    __all__.extend(["DocxDirectLoader", "DocxDirectoryLoader"])
except ImportError:
    pass

# Vision providers (optional import)
try:
    from .vision import create_vision_provider, VisionProvider
    __all__.extend(["create_vision_provider", "VisionProvider"])
except ImportError:
    pass
