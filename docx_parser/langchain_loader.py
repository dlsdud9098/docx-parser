"""
LangChain compatible document loader for DOCX files with rich metadata support.

Provides LangChain Document loaders that extract:
- Text content with [IMAGE_N] placeholders
- DOCX metadata (author, title, page count, etc.)
- Image extraction and mapping
- Vision-based image descriptions (optional)
"""

from pathlib import Path
from typing import List, Optional, Iterator, Dict, Any, TYPE_CHECKING

try:
    from langchain_core.document_loaders import BaseLoader
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.document_loaders.base import BaseLoader
        from langchain.schema import Document
    except ImportError:
        raise ImportError(
            "LangChain is required for this module. "
            "Install with: pip install docx-parser[langchain]"
        )

if TYPE_CHECKING:
    from .vision.base import VisionProvider

from .parser import (
    DocxParser,
    ParseResult,
    VerticalMergeMode,
    HorizontalMergeMode,
    OutputFormat,
    HierarchyMode,
)


class DocxDirectLoader(BaseLoader):
    """
    LangChain document loader for DOCX files with rich metadata extraction.

    Extracts text with [IMAGE_N] placeholders, saves images separately,
    and provides comprehensive DOCX metadata compatible with LangChain.

    Example:
        # Basic usage
        loader = DocxDirectLoader("document.docx", output_dir="output")
        docs = loader.load()

        # Access metadata
        doc = docs[0]
        print(doc.metadata["author"])        # Document author
        print(doc.metadata["total_pages"])   # Page count
        print(doc.metadata["created_date"])  # Creation date
        print(doc.metadata["images"])        # Image list

        # With text output format
        loader = DocxDirectLoader("document.docx", output_format="text")
        docs = loader.load()

        # With vision provider for automatic image description
        from docx_parser.vision import create_vision_provider
        provider = create_vision_provider("openai")
        loader = DocxDirectLoader("document.docx",
                                 vision_provider=provider,
                                 auto_describe_images=True)
        docs = loader.load()

        # Use with text splitter
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
        chunks = splitter.split_documents(docs)
    """

    def __init__(
        self,
        file_path: str | Path,
        output_dir: Optional[str | Path] = None,
        extract_images: bool = True,
        image_placeholder: str = "[IMAGE_{num}]",
        vertical_merge: VerticalMergeMode | str = VerticalMergeMode.REPEAT,
        horizontal_merge: HorizontalMergeMode | str = HorizontalMergeMode.EXPAND,
        output_format: OutputFormat | str = OutputFormat.MARKDOWN,
        extract_metadata: bool = True,
        hierarchy_mode: HierarchyMode | str = HierarchyMode.NONE,
        max_heading_level: int = 6,
        vision_provider: Optional["VisionProvider"] = None,
        auto_describe_images: bool = False,
    ):
        """
        Initialize the loader.

        Args:
            file_path: Path to DOCX file
            output_dir: Directory to save extracted images
            extract_images: Whether to extract images to files
            image_placeholder: Format string for image placeholders
            vertical_merge: How to handle vertically merged cells
                - "repeat": Repeat the value in merged cells (default)
                - "empty": Keep merged cells empty
                - "first": Only show value in first cell
            horizontal_merge: How to handle horizontally merged cells
                - "expand": Expand to multiple empty cells (default)
                - "single": Keep as single cell (ignore span)
                - "repeat": Repeat value in spanned cells
            output_format: Output format for content
                - "markdown": Markdown format with tables (default)
                - "text": Plain text without markdown formatting
                - "json": Structured JSON output
            extract_metadata: Whether to extract DOCX metadata (default: True)
            hierarchy_mode: How to detect heading hierarchy
                - "none": No heading detection (default)
                - "auto": Style first, font_size fallback
                - "style": Use styles.xml outlineLevel only
                - "font_size": Use font size only
            max_heading_level: Maximum heading depth (1-6, default: 6)
            vision_provider: VisionProvider instance for image description (optional)
            auto_describe_images: Automatically generate image descriptions (default: False)
        """
        self.file_path = Path(file_path)
        self.output_dir = Path(output_dir) if output_dir else None
        self.extract_images = extract_images
        self.image_placeholder = image_placeholder
        self.output_format = OutputFormat(output_format)
        self.extract_metadata = extract_metadata
        self.hierarchy_mode = HierarchyMode(hierarchy_mode)
        self.max_heading_level = max_heading_level
        self.vision_provider = vision_provider
        self.auto_describe_images = auto_describe_images
        self._parser = DocxParser(
            extract_images=extract_images,
            image_placeholder=image_placeholder,
            vertical_merge=vertical_merge,
            horizontal_merge=horizontal_merge,
            output_format=output_format,
            extract_metadata=extract_metadata,
            hierarchy_mode=hierarchy_mode,
            max_heading_level=max_heading_level,
        )

    def load(self) -> List[Document]:
        """
        Load DOCX file and return as LangChain Document with rich metadata.

        Returns:
            List containing single Document with parsed content and metadata
        """
        result = self._parser.parse(self.file_path, self.output_dir)

        # Auto-generate image descriptions if requested
        if self.auto_describe_images and self.vision_provider and result.images_list:
            result.describe_images(self.vision_provider)
            content = result.replace_placeholders(result.image_descriptions)
        else:
            content = result.content

        # Use the built-in LangChain metadata generation
        metadata = result.to_langchain_metadata()

        # Add image descriptions to metadata if available
        if result.image_descriptions:
            metadata["image_descriptions"] = result.image_descriptions

        # Add image_dir if output_dir was specified
        if self.output_dir:
            metadata["image_dir"] = str(self.output_dir / "images" / self.file_path.stem)

        return [Document(
            page_content=content,
            metadata=metadata
        )]

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load - yields documents one at a time"""
        yield from self.load()


class DocxDirectoryLoader(BaseLoader):
    """
    Load all DOCX files from a directory with rich metadata.

    Example:
        loader = DocxDirectoryLoader("documents/", output_dir="output")
        docs = loader.load()

        for doc in docs:
            print(f"File: {doc.metadata['file_name']}")
            print(f"Author: {doc.metadata.get('author', 'Unknown')}")
            print(f"Pages: {doc.metadata.get('total_pages', 'N/A')}")

        # With vision provider
        from docx_parser.vision import create_vision_provider
        provider = create_vision_provider("openai")
        loader = DocxDirectoryLoader("documents/",
                                    vision_provider=provider,
                                    auto_describe_images=True)
    """

    def __init__(
        self,
        directory: str | Path,
        output_dir: Optional[str | Path] = None,
        glob_pattern: str = "**/*.docx",
        extract_images: bool = True,
        vertical_merge: VerticalMergeMode | str = VerticalMergeMode.REPEAT,
        horizontal_merge: HorizontalMergeMode | str = HorizontalMergeMode.EXPAND,
        output_format: OutputFormat | str = OutputFormat.MARKDOWN,
        extract_metadata: bool = True,
        hierarchy_mode: HierarchyMode | str = HierarchyMode.NONE,
        max_heading_level: int = 6,
        vision_provider: Optional["VisionProvider"] = None,
        auto_describe_images: bool = False,
    ):
        """
        Initialize directory loader.

        Args:
            directory: Directory containing DOCX files
            output_dir: Directory to save extracted images
            glob_pattern: Pattern to match DOCX files
            extract_images: Whether to extract images
            vertical_merge: How to handle vertically merged cells
            horizontal_merge: How to handle horizontally merged cells
            output_format: Output format for content
            extract_metadata: Whether to extract DOCX metadata
            hierarchy_mode: How to detect heading hierarchy
            max_heading_level: Maximum heading depth (1-6)
            vision_provider: VisionProvider instance for image description (optional)
            auto_describe_images: Automatically generate image descriptions (default: False)
        """
        self.directory = Path(directory)
        self.output_dir = Path(output_dir) if output_dir else None
        self.glob_pattern = glob_pattern
        self.extract_images = extract_images
        self.vertical_merge = vertical_merge
        self.horizontal_merge = horizontal_merge
        self.output_format = OutputFormat(output_format)
        self.extract_metadata = extract_metadata
        self.hierarchy_mode = HierarchyMode(hierarchy_mode)
        self.max_heading_level = max_heading_level
        self.vision_provider = vision_provider
        self.auto_describe_images = auto_describe_images

    def load(self) -> List[Document]:
        """Load all DOCX files from directory"""
        documents = []

        for docx_path in self.directory.glob(self.glob_pattern):
            loader = DocxDirectLoader(
                docx_path,
                output_dir=self.output_dir,
                extract_images=self.extract_images,
                vertical_merge=self.vertical_merge,
                horizontal_merge=self.horizontal_merge,
                output_format=self.output_format,
                extract_metadata=self.extract_metadata,
                hierarchy_mode=self.hierarchy_mode,
                max_heading_level=self.max_heading_level,
                vision_provider=self.vision_provider,
                auto_describe_images=self.auto_describe_images,
            )
            documents.extend(loader.load())

        return documents

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load - yields documents one at a time"""
        for docx_path in self.directory.glob(self.glob_pattern):
            loader = DocxDirectLoader(
                docx_path,
                output_dir=self.output_dir,
                extract_images=self.extract_images,
                vertical_merge=self.vertical_merge,
                horizontal_merge=self.horizontal_merge,
                output_format=self.output_format,
                extract_metadata=self.extract_metadata,
                hierarchy_mode=self.hierarchy_mode,
                max_heading_level=self.max_heading_level,
                vision_provider=self.vision_provider,
                auto_describe_images=self.auto_describe_images,
            )
            yield from loader.load()
