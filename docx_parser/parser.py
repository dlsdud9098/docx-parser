"""
Core DOCX parser - extracts text with image placeholders and metadata.

Refactored version using processors for cleaner architecture.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple, Union

from .models import (
    HierarchyMode,
    HorizontalMergeMode,
    ImageInfo,
    OutputFormat,
    ParseResult,
    StyleInfo,
    TableFormat,
    VerticalMergeMode,
)
from .processors import (
    ContentProcessor,
    ImageProcessor,
    MetadataProcessor,
    ParsingContext,
    StyleProcessor,
    TableProcessor,
)
from .utils.xml import METADATA_NAMESPACES, NAMESPACES

if TYPE_CHECKING:
    from typing import Callable

    from .models import TableInfo
    from .vision.base import VisionProvider


class DocxParser:
    """
    DOCX Parser that extracts text with image placeholders and metadata.

    Example:
        parser = DocxParser()
        result = parser.parse("document.docx", output_dir="output")
        print(result.content)  # Markdown with [IMAGE_N] placeholders
        print(result.images)   # {1: Path("output/images/001_image.png"), ...}
        print(result.metadata.core.creator)  # Author
        print(result.metadata.app.pages)     # Page count
    """

    # Class attributes for backward compatibility
    NAMESPACES = NAMESPACES
    METADATA_NAMESPACES = METADATA_NAMESPACES

    def __init__(
        self,
        extract_images: bool = True,
        image_placeholder: str = "[IMAGE_{num}]",
        vertical_merge: VerticalMergeMode | str = VerticalMergeMode.REPEAT,
        horizontal_merge: HorizontalMergeMode | str = HorizontalMergeMode.EXPAND,
        output_format: OutputFormat | str = OutputFormat.MARKDOWN,
        extract_metadata: bool = True,
        hierarchy_mode: HierarchyMode | str = HierarchyMode.NONE,
        max_heading_level: int = 6,
        table_format: TableFormat | str = TableFormat.MARKDOWN,
        convert_images: bool = True,
        heading_patterns: Optional[List[Tuple[str, int]]] = None,
        extract_tables: bool = False,
    ):
        """Initialize parser with configuration options."""
        # Store config
        self.extract_images = extract_images
        self.image_placeholder = image_placeholder
        self.vertical_merge = VerticalMergeMode(vertical_merge)
        self.horizontal_merge = HorizontalMergeMode(horizontal_merge)
        self.output_format = OutputFormat(output_format)
        self.convert_images = convert_images
        self.extract_metadata_flag = extract_metadata
        self.hierarchy_mode = HierarchyMode(hierarchy_mode)
        self.max_heading_level = min(max(1, max_heading_level), 6)
        self.table_format = TableFormat(table_format)
        self._heading_patterns = heading_patterns
        self.extract_tables = extract_tables

        # Initialize processors
        self._init_processors()

    def _init_processors(self) -> None:
        """Initialize all processor instances."""
        # Table processor
        self._table_processor = TableProcessor(
            vertical_merge=self.vertical_merge,
            horizontal_merge=self.horizontal_merge,
            table_format=self.table_format,
            extract=self.extract_tables,
        )

        # Content processor (uses table processor internally)
        self._content_processor = ContentProcessor(
            hierarchy_mode=self.hierarchy_mode,
            max_heading_level=self.max_heading_level,
            heading_patterns=self._compile_patterns(),
            image_placeholder=self.image_placeholder,
            output_format=self.output_format,
            table_processor=self._table_processor,
        )

        # Other processors
        self._style_processor = StyleProcessor()
        self._metadata_processor = MetadataProcessor()
        self._image_processor = ImageProcessor(
            extract_images=self.extract_images,
            convert_images=self.convert_images,
            image_placeholder=self.image_placeholder,
        )

    def _compile_patterns(self) -> Optional[List[Tuple]]:
        """Compile heading patterns to regex."""
        if not self._heading_patterns:
            return None

        import re
        compiled = []
        for pattern_str, level in self._heading_patterns:
            regex = self._convert_to_regex(pattern_str)
            try:
                compiled.append((re.compile(regex), level))
            except re.error as e:
                raise ValueError(f"Invalid heading pattern '{pattern_str}': {e}")
        return compiled if compiled else None

    def _convert_to_regex(self, pattern: str) -> str:
        """Convert user-friendly pattern to regex."""
        import re

        if pattern.startswith('^'):
            return pattern

        # Pattern templates (공백 유무 모두 지원)
        conversions = [
            # 로마숫자 + 점 (I. II. III.)
            (r'^[IVXLCDMivxlcdm]+\. ?$', r'^[IVXLCDMivxlcdm]+\. '),
            # 숫자 + 점 (1. 2. 3.)
            (r'^\d+\. ?$', r'^\d+\. '),
            # 숫자 + 닫는 괄호 (1) 2) 3))
            (r'^\d+\) ?$', r'^\d+\) '),
            # 괄호 + 숫자 ((1) (2) (3))
            (r'^\(\d+\) ?$', r'^\(\d+\) '),
            # 대문자 + 점 (A. B. C.)
            (r'^[A-Z]+\. ?$', r'^[A-Z]+\. '),
            # 소문자 + 점 (a. b. c.)
            (r'^[a-z]+\. ?$', r'^[a-z]+\. '),
            # 한글 + 점 (가. 나. 다.)
            (r'^[가-힣]\. ?$', r'^[가-힣]\. '),
            # 원숫자 (① ② ③)
            (r'^[①②③④⑤⑥⑦⑧⑨⑩] ?$', r'^[①②③④⑤⑥⑦⑧⑨⑩] ?'),
        ]

        for check, result in conversions:
            if re.match(check, pattern):
                return result

        return f'^{re.escape(pattern)}'

    def parse(
        self,
        docx_path: str | Path,
        output_dir: Optional[str | Path] = None
    ) -> ParseResult:
        """
        Parse DOCX file.

        Args:
            docx_path: Path to DOCX file
            output_dir: Directory to save images and tables (optional)

        Returns:
            ParseResult with content, image information, tables, and metadata
        """
        docx_path = Path(docx_path)

        # Prepare output directory
        img_dir = None
        table_dir = None
        if output_dir:
            output_dir = Path(output_dir)
            img_dir = output_dir / "images" / docx_path.stem
            img_dir.mkdir(parents=True, exist_ok=True)
            if self.extract_tables:
                table_dir = output_dir / "tables" / docx_path.stem
                table_dir.mkdir(parents=True, exist_ok=True)

        # Configure table processor for this document
        self._table_processor._source_doc = str(docx_path)
        self._table_processor._output_dir = table_dir
        self._table_processor.reset()

        with zipfile.ZipFile(docx_path, 'r') as z:
            # Create parsing context
            context = ParsingContext(zip_file=z)

            # Extract metadata
            metadata = None
            if self.extract_metadata_flag:
                metadata = self._metadata_processor.process(context, docx_path=docx_path)

            # Process images
            images, image_mapping, images_list = self._image_processor.process(
                context, output_dir=img_dir, docx_stem=docx_path.stem
            )

            # Load styles if needed for hierarchy detection
            styles: Dict[str, StyleInfo] = {}
            font_size_hierarchy: Dict[int, int] = {}

            if self.hierarchy_mode != HierarchyMode.NONE:
                styles = self._style_processor.process(context)
                if self.hierarchy_mode in (HierarchyMode.AUTO, HierarchyMode.FONT_SIZE):
                    doc_xml = z.read("word/document.xml").decode('utf-8')
                    font_size_hierarchy = self._style_processor.build_hierarchy(
                        doc_xml, styles, self.max_heading_level
                    )

            # Parse document content
            doc_xml = z.read("word/document.xml").decode('utf-8')

            # Get rid_to_num from context (set by ImageProcessor)
            rid_to_num = context.rid_to_num or {}

        # Parse content
        markdown_content = self._content_processor.parse_content(
            doc_xml, rid_to_num, styles, font_size_hierarchy
        )
        text_content = ContentProcessor.to_text(markdown_content)

        # Determine final content based on output format
        if self.output_format == OutputFormat.TEXT:
            content = text_content
        elif self.output_format == OutputFormat.JSON:
            content = self._content_processor.parse_content_blocks(
                doc_xml, rid_to_num, styles, font_size_hierarchy
            )
        else:
            content = markdown_content

        # Collect extracted tables
        tables_list = self._table_processor.extracted_tables

        return ParseResult(
            content=content,
            images=images,
            image_mapping=image_mapping,
            source=docx_path,
            image_count=len(images_list),
            metadata=metadata,
            images_list=images_list,
            output_format=self.output_format,
            text_content=text_content,
            markdown_content=markdown_content,
            tables_list=tables_list,
        )

    # Backward compatibility properties
    @property
    def heading_patterns(self):
        """Return compiled heading patterns for backward compatibility."""
        return self._compile_patterns()


def parse_docx(
    docx_path: Union[str, Path, List[str], List[Path]],
    output_dir: Optional[str | Path] = None,
    extract_images: bool = True,
    vertical_merge: VerticalMergeMode | str = VerticalMergeMode.REPEAT,
    horizontal_merge: HorizontalMergeMode | str = HorizontalMergeMode.EXPAND,
    output_format: OutputFormat | str = OutputFormat.MARKDOWN,
    extract_metadata: bool = True,
    hierarchy_mode: HierarchyMode | str = HierarchyMode.NONE,
    max_heading_level: int = 6,
    table_format: TableFormat | str = TableFormat.MARKDOWN,
    vision_provider: Optional["VisionProvider"] = None,
    auto_describe_images: bool = False,
    image_prompts: Optional[Dict[int, str]] = None,
    save_file: bool = False,
    convert_images: bool = True,
    heading_patterns: Optional[List[Tuple[str, int]]] = None,
    extract_tables: bool = False,
    auto_summarize_tables: Union[
        bool,
        Literal["openai", "claude", "gemini", "cerebras"],
        List[Literal["openai", "claude", "gemini", "cerebras"]]
    ] = False,
    summarizer_max_tokens: int = 200,
    year: Optional[int] = None,
) -> Union[ParseResult, List[ParseResult]]:
    """
    Convenience function to parse DOCX file(s).

    Args:
        docx_path: Path to DOCX file, or list of paths for batch processing
        output_dir: Directory to save images and tables
        extract_images: Whether to extract images
        vertical_merge: How to handle vertically merged cells
        horizontal_merge: How to handle horizontally merged cells
        output_format: Output format for content
        extract_metadata: Whether to extract DOCX metadata
        hierarchy_mode: How to detect heading hierarchy
        max_heading_level: Maximum heading depth (1-6)
        table_format: Output format for tables
        vision_provider: VisionProvider instance for image description
        auto_describe_images: Automatically generate image descriptions
        image_prompts: Dictionary mapping image index to custom prompt
        save_file: Whether to save content file when output_dir is specified
        convert_images: Convert non-standard image formats to PNG
        heading_patterns: Custom patterns for hierarchy_mode="pattern"
        extract_tables: Whether to extract tables to separate files
        auto_summarize_tables: Provider(s) for table summarization
            - False: No summarization (default)
            - "openai": Use OpenAI API (gpt-4o-mini)
            - "claude": Use Anthropic Claude API (claude-3-5-haiku)
            - "gemini": Use Google Gemini API (gemini-2.0-flash)
            - "cerebras": Use Cerebras API (llama-3.3-70b)
            - ["cerebras", "openai", ...]: Fallback order (try first, if fails try next)
        summarizer_max_tokens: Max tokens for table summary (default: 200)
        year: Document year (e.g., 2022). If not specified, auto-extracted from filename.

    Returns:
        ParseResult (single file) or List[ParseResult] (multiple files)
    """
    parser = DocxParser(
        extract_images=extract_images,
        vertical_merge=vertical_merge,
        horizontal_merge=horizontal_merge,
        output_format=output_format,
        extract_metadata=extract_metadata,
        hierarchy_mode=hierarchy_mode,
        max_heading_level=max_heading_level,
        table_format=table_format,
        convert_images=convert_images,
        heading_patterns=heading_patterns,
        extract_tables=extract_tables,
    )

    def _save_result(result: ParseResult, out_dir: Path, fmt: OutputFormat) -> None:
        """Save result based on output_format."""
        if not out_dir:
            return
        base_name = result.source.stem if result.source else "output"
        if fmt == OutputFormat.MARKDOWN:
            result.save_markdown(out_dir / f"{base_name}.md")
        elif fmt == OutputFormat.TEXT:
            result.save_text(out_dir / f"{base_name}.txt")
        elif fmt == OutputFormat.JSON:
            result.save_json(out_dir / f"{base_name}.json")

    def _process_result(result: ParseResult) -> None:
        """Process image and table descriptions for a result."""
        # Set year in metadata (user-specified takes priority)
        if year and result.metadata:
            result.metadata.year = year

        # Handle image descriptions
        if auto_describe_images and vision_provider and result.images_list:
            result.describe_images(vision_provider, image_prompts=image_prompts)
            result.content = result.replace_placeholders(result.image_descriptions)
            result.markdown_content = result.content  # Update markdown_content too

        # Handle table descriptions
        if auto_summarize_tables and result.tables_list:
            # Normalize providers to list
            if isinstance(auto_summarize_tables, str):
                providers = [auto_summarize_tables]
            elif isinstance(auto_summarize_tables, list):
                providers = auto_summarize_tables
            else:
                providers = []

            if providers:
                from .summarizer import create_table_summarizer

                summaries = None
                last_error = None

                # Try each provider in order
                for provider in providers:
                    try:
                        summarizer = create_table_summarizer(
                            provider=provider,
                            max_tokens=summarizer_max_tokens,
                        )
                        summaries = summarizer.summarize_tables(result.tables_list, delay=0.5)
                        break  # Success, stop trying
                    except Exception as e:
                        last_error = e
                        continue  # Try next provider

                if summaries:
                    result.table_descriptions = summaries
                else:
                    # All providers failed, use file paths as fallback
                    result.describe_tables(summarizer=None)
                    if last_error:
                        import warnings
                        warnings.warn(f"All summarizers failed. Last error: {last_error}")
            else:
                # No provider specified, just use file paths
                result.describe_tables(summarizer=None)

            result.content = result.replace_table_placeholders(result.table_descriptions)
            result.markdown_content = result.content  # Update markdown_content too

    # Handle list of paths
    if isinstance(docx_path, list):
        results = []
        for path in docx_path:
            result = parser.parse(path, output_dir)
            _process_result(result)
            if output_dir and save_file:
                _save_result(result, Path(output_dir), OutputFormat(output_format))
            results.append(result)
        return results

    # Single path
    result = parser.parse(docx_path, output_dir)
    _process_result(result)

    if output_dir and save_file:
        _save_result(result, Path(output_dir), OutputFormat(output_format))

    return result
