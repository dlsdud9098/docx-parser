"""
docx-parser: DOCX parser with image extraction, metadata, vision, and LangChain integration

Features:
- Text extraction with [IMAGE_N] placeholders
- DOCX metadata extraction (author, title, page count, etc.)
- Multiple output formats (markdown, text, json)
- Multimodal vision for image description (OpenAI, Anthropic, Google, Transformers)
- LangChain Document compatible
"""

# Import from models package
from .models import (
    # Enums
    VerticalMergeMode,
    HorizontalMergeMode,
    OutputFormat,
    HierarchyMode,
    TableFormat,
    BlockType,
    # Type alias
    HeadingPattern,
    # Image
    ImageInfo,
    StyleInfo,
    # Blocks
    ParagraphBlock,
    HeadingBlock,
    TableBlock,
    ImageBlock,
    # Metadata
    CoreMetadata,
    AppMetadata,
    DocxMetadata,
    # Table
    TableCell,
    TableData,
    TableInfo,
    # Result
    ParseResult,
)

# Import from parser
from .parser import (
    DocxParser,
    parse_docx,
)

__version__ = "0.4.0"
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
    "BlockType",
    # Type aliases
    "HeadingPattern",
    # Metadata classes
    "DocxMetadata",
    "CoreMetadata",
    "AppMetadata",
    "ImageInfo",
    "StyleInfo",
    # Block classes
    "ParagraphBlock",
    "HeadingBlock",
    "TableBlock",
    "ImageBlock",
    # Table classes
    "TableCell",
    "TableData",
    "TableInfo",
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

# Table summarizers (optional import)
try:
    from .summarizer import create_table_summarizer, TableSummarizer
    __all__.extend(["create_table_summarizer", "TableSummarizer"])
except ImportError:
    pass
