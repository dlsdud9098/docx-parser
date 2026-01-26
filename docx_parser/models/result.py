"""
ParseResult model for docx_parser.

This module contains the ParseResult dataclass, the main result object from parsing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .enums import OutputFormat
from .image import ImageInfo
from .metadata import DocxMetadata
from .table import TableInfo

if TYPE_CHECKING:
    from typing import Callable

    from ..vision.base import VisionProvider


@dataclass
class ParseResult:
    """Result of parsing a DOCX file.

    Attributes:
        content: Parsed content as string (markdown/text) or list of blocks (json).
        images: Mapping of image index to image path (backward compatibility).
        image_mapping: Mapping of image index to filename (backward compatibility).
        source: Path to the source DOCX file.
        image_count: Total number of images extracted.
        metadata: DOCX metadata (author, title, page count, etc.).
        images_list: List of ImageInfo objects with detailed image info.
        output_format: Format of the content field.
        text_content: Plain text version of content (always available).
        markdown_content: Markdown version of content (always available).
        image_descriptions: Vision-generated image descriptions.
        tables_list: List of TableInfo objects with extracted table info.
        table_descriptions: Table summaries (LLM-generated or file paths).

    Example:
        >>> result = parse_docx("document.docx")
        >>> print(result.content)
        >>> print(result.image_count)
        >>> result.save_markdown("output.md")
    """
    content: Union[str, List[Dict[str, Any]]]
    images: Dict[int, Path] = field(default_factory=dict)
    image_mapping: Dict[int, str] = field(default_factory=dict)
    source: Optional[Path] = None
    image_count: int = 0
    metadata: Optional[DocxMetadata] = None
    images_list: List[ImageInfo] = field(default_factory=list)
    output_format: OutputFormat = OutputFormat.MARKDOWN
    text_content: Optional[str] = None
    markdown_content: Optional[str] = None
    image_descriptions: Dict[int, str] = field(default_factory=dict)
    tables_list: List[TableInfo] = field(default_factory=list)
    table_descriptions: Dict[int, str] = field(default_factory=dict)

    def save_markdown(self, path: str | Path) -> Path:
        """Save content to markdown file.

        Args:
            path: Output file path.

        Returns:
            Path to the saved file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.markdown_content if self.markdown_content else self.content
        if isinstance(content, list):
            content = self.markdown_content or ""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def save_text(self, path: str | Path) -> Path:
        """Save plain text content to file.

        Args:
            path: Output file path.

        Returns:
            Path to the saved file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.text_content if self.text_content else self.content
        if isinstance(content, list):
            content = self.text_content or ""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def save_json(self, path: str | Path) -> Path:
        """Save structured JSON to file.

        Args:
            path: Output file path.

        Returns:
            Path to the saved file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        return path

    def save_mapping(self, path: str | Path) -> Path:
        """Save image mapping to file.

        Args:
            path: Output file path.

        Returns:
            Path to the saved file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for num, filename in sorted(self.image_mapping.items()):
                f.write(f"[IMAGE_{num}] -> {filename}\n")
        return path

    def get_image_path(self, num: int) -> Optional[Path]:
        """Get image path by number.

        Args:
            num: Image index number.

        Returns:
            Path to the image file, or None if not found.
        """
        return self.images.get(num)

    def replace_placeholders(self, descriptions: Dict[int, str]) -> str:
        """Replace [IMAGE_N] placeholders with image link and descriptions.

        Args:
            descriptions: Mapping of image index to description text.

        Returns:
            Content with placeholders replaced.

        Output format:
            ![IMAGE_N](path/to/image.png)

            Description text...
        """
        content = self.content
        if isinstance(content, list):
            content = self.markdown_content or ""

        image_paths = {img.index: img.path for img in self.images_list}

        for num, desc in descriptions.items():
            path = image_paths.get(num)
            if path:
                replacement = f"\n\n![IMAGE_{num}]({path})\n\n{desc}\n\n"
            else:
                replacement = f"\n\n[Image: {desc}]\n\n"
            content = content.replace(f"[IMAGE_{num}]", replacement)

        return content

    def describe_images(
        self,
        provider: "VisionProvider",
        force: bool = False,
        image_prompts: Optional[Dict[int, str]] = None,
    ) -> Dict[int, str]:
        """Generate image descriptions using a vision provider.

        Args:
            provider: VisionProvider instance.
            force: If True, overwrite existing descriptions.
            image_prompts: Optional mapping of image index to custom prompt.
                Each image can use a different prompt.
                Example: {1: "Analyze this diagram...", 2: "Describe this chart..."}

        Returns:
            Mapping of image index to description text.

        Example:
            >>> from docx_parser.vision import create_vision_provider
            >>> provider = create_vision_provider("openai")
            >>> descriptions = result.describe_images(provider)
            >>> descriptions = result.describe_images(provider, image_prompts={
            ...     1: "Analyze this technical diagram...",
            ...     2: "Describe the trend in this chart...",
            ... })
        """
        if self.image_descriptions and not force:
            return self.image_descriptions

        images_with_path = [
            img for img in self.images_list
            if img.path
        ]

        if not images_with_path:
            return {}

        self.image_descriptions = provider.describe_images(
            images_with_path,
            image_prompts=image_prompts
        )
        return self.image_descriptions

    def describe_tables(
        self,
        summarizer: Optional["Callable[[TableInfo], str]"] = None,
        force: bool = False,
    ) -> Dict[int, str]:
        """Generate table summaries.

        Args:
            summarizer: Function that takes TableInfo and returns summary string.
                If None, uses file path as summary.
            force: If True, overwrite existing descriptions.

        Returns:
            Mapping of table index to summary text.

        Example:
            >>> # With LLM summarizer
            >>> def llm_summarize(table: TableInfo) -> str:
            ...     return llm.invoke(f"Summarize: {table.headers}")
            >>> descriptions = result.describe_tables(summarizer=llm_summarize)

            >>> # Without summarizer (uses file path)
            >>> descriptions = result.describe_tables()
        """
        if self.table_descriptions and not force:
            return self.table_descriptions

        for table in self.tables_list:
            if summarizer:
                try:
                    summary = summarizer(table)
                except Exception as e:
                    summary = f"[Table summary failed: {e}]"
            else:
                # summarizer 없으면 테이블 기본 정보 사용
                summary = f"Table {table.index} ({table.row_count}x{table.col_count})"

            self.table_descriptions[table.index] = summary

        return self.table_descriptions

    def replace_table_placeholders(
        self,
        descriptions: Optional[Dict[int, str]] = None,
    ) -> str:
        """Replace [TABLE_N] placeholders with summaries and links.

        Args:
            descriptions: Mapping of table index to description.
                If None, uses self.table_descriptions.

        Returns:
            Content with placeholders replaced.

        Output format:
            [TABLE_N: summary](path/to/table.json)
        """
        content = self.content
        if isinstance(content, list):
            content = self.markdown_content or ""

        descs = descriptions or self.table_descriptions
        table_paths = {t.index: t.path for t in self.tables_list}

        for num, desc in descs.items():
            path = table_paths.get(num, "")
            if path:
                replacement = f"\n\n[TABLE_{num}: {desc}]({path})\n\n"
            else:
                replacement = f"\n\n[TABLE_{num}: {desc}]\n\n"
            content = content.replace(f"[TABLE_{num}]", replacement)

        return content

    def get_described_content(
        self,
        provider: Optional["VisionProvider"] = None,
        descriptions: Optional[Dict[int, str]] = None,
    ) -> str:
        """Get content with image descriptions included.

        Args:
            provider: VisionProvider for generating descriptions.
            descriptions: Pre-generated descriptions dictionary.

        Returns:
            Content with [IMAGE_N] replaced by descriptions.

        Example:
            >>> # Method 1: Use pre-generated descriptions
            >>> result.describe_images(provider)
            >>> content = result.get_described_content()

            >>> # Method 2: Generate descriptions inline
            >>> content = result.get_described_content(provider=provider)

            >>> # Method 3: Provide custom descriptions
            >>> content = result.get_described_content(descriptions={1: "Logo", 2: "Chart"})
        """
        if descriptions:
            return self.replace_placeholders(descriptions)

        if provider:
            descs = self.describe_images(provider)
            return self.replace_placeholders(descs)

        if self.image_descriptions:
            return self.replace_placeholders(self.image_descriptions)

        content = self.content
        if isinstance(content, list):
            return self.markdown_content or ""
        return content

    def to_json(self) -> str:
        """Convert ParseResult to JSON string.

        Returns:
            JSON string representation.
        """
        if isinstance(self.content, list):
            content_data = self.content
        else:
            content_data = self.text_content or self.content

        data = {
            "content": content_data,
            "image_count": self.image_count,
            "images": [img.to_dict() for img in self.images_list],
            "table_count": len(self.tables_list),
            "tables": [t.to_dict() for t in self.tables_list],
            "source": str(self.source) if self.source else None,
            "metadata": self.metadata.to_dict() if self.metadata else {}
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def to_langchain_metadata(self) -> Dict[str, Any]:
        """Generate LangChain-compatible metadata dictionary.

        Returns:
            Dictionary with LangChain standard metadata fields.
        """
        meta: Dict[str, Any] = {
            "source": str(self.source) if self.source else None,
            "page": 1,
            "file_type": "docx",
            "image_count": self.image_count,
        }
        if self.metadata:
            meta.update(self.metadata.to_dict())
        if self.images_list:
            meta["images"] = [img.to_dict() for img in self.images_list]
        if self.image_mapping:
            meta["image_mapping"] = self.image_mapping
        if self.tables_list:
            meta["table_count"] = len(self.tables_list)
            meta["tables"] = [t.to_dict() for t in self.tables_list]
        return meta

    def to_langchain_documents(
        self,
        described: bool = False,
        provider: Optional["VisionProvider"] = None,
    ) -> List[Any]:
        """Convert ParseResult to LangChain Document list.

        Similar to LlamaParse's get_markdown_documents() / get_text_documents().

        Args:
            described: If True, use content with image descriptions.
            provider: VisionProvider to generate descriptions (optional).

        Returns:
            List of LangChain Document objects.

        Raises:
            ImportError: If langchain is not installed.

        Example:
            >>> from docx_parser import parse_docx
            >>> result = parse_docx("document.docx")
            >>> docs = result.to_langchain_documents()

            >>> # With image descriptions
            >>> from docx_parser.vision import create_vision_provider
            >>> provider = create_vision_provider("openai")
            >>> docs = result.to_langchain_documents(described=True, provider=provider)
        """
        try:
            from langchain_core.documents import Document
        except ImportError:
            raise ImportError(
                "langchain is required for to_langchain_documents(). "
                "Install with: pip install docx-parser[langchain]"
            )

        if described and provider:
            content = self.get_described_content(provider=provider)
        elif described and self.image_descriptions:
            content = self.get_described_content()
        else:
            content = self.content
            if isinstance(content, list):
                content = self.markdown_content or ""

        metadata = self.to_langchain_metadata()

        return [Document(page_content=content, metadata=metadata)]

    def to_llama_index_documents(
        self,
        described: bool = False,
        provider: Optional["VisionProvider"] = None,
    ) -> List[Any]:
        """Convert ParseResult to LlamaIndex Document list.

        Similar to LlamaParse's result object pattern.

        Args:
            described: If True, use content with image descriptions.
            provider: VisionProvider to generate descriptions (optional).

        Returns:
            List of LlamaIndex Document objects.

        Raises:
            ImportError: If llama-index is not installed.

        Example:
            >>> from docx_parser import parse_docx
            >>> result = parse_docx("document.docx")
            >>> docs = result.to_llama_index_documents()

            >>> # Use with LlamaIndex
            >>> from llama_index.core import VectorStoreIndex
            >>> index = VectorStoreIndex.from_documents(docs)
        """
        try:
            from llama_index.core import Document
        except ImportError:
            raise ImportError(
                "llama-index is required for to_llama_index_documents(). "
                "Install with: pip install llama-index"
            )

        if described and provider:
            content = self.get_described_content(provider=provider)
        elif described and self.image_descriptions:
            content = self.get_described_content()
        else:
            content = self.content
            if isinstance(content, list):
                content = self.markdown_content or ""

        metadata = self.to_langchain_metadata()

        return [Document(text=content, metadata=metadata)]
