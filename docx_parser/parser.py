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

        # Prepare output directory: output/{docx_stem}/images, output/{docx_stem}/tables
        img_dir = None
        table_dir = None
        doc_output_dir = None
        if output_dir:
            output_dir = Path(output_dir)
            doc_output_dir = output_dir / docx_path.stem
            img_dir = doc_output_dir / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            if self.extract_tables:
                table_dir = doc_output_dir / "tables"
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


def update_markdown_with_images(
    docx_path: Union[str, Path],
    markdown_path: Union[str, Path],
    vision_provider: Union[
        str,
        List[str],
        "VisionProvider",
    ] = "openai",
    image_prompts: Optional[Dict[int, str]] = None,
    vision_max_tokens: int = 300,
    vision_model: Optional[str] = None,
    vision_load_in_4bit: bool = False,
    vision_load_in_8bit: bool = False,
    vision_batch_size: int = 4,
    save: bool = True,
) -> str:
    """
    기존 마크다운 파일에 이미지 설명만 추가합니다.
    테이블 요약은 그대로 유지됩니다.

    Args:
        docx_path: 원본 DOCX 파일 경로
        markdown_path: 업데이트할 마크다운 파일 경로
        vision_provider: Vision AI 제공자 또는 VisionProvider 인스턴스
            - "openai": OpenAI gpt-4o (기본값)
            - "anthropic": Anthropic Claude
            - "gemini" or "google": Google Gemini
            - "transformers": 로컬 LLaVA 모델
            - ["gemini", "openai", ...]: 폴백 순서
            - VisionProvider 인스턴스: 직접 제공
        image_prompts: 이미지별 커스텀 프롬프트 {이미지번호: 프롬프트}
        vision_max_tokens: Vision AI 최대 토큰 수 (기본: 300)
        vision_model: Vision 모델 ID (예: "gpt-4o-mini")
        vision_load_in_4bit: Transformers 4bit 양자화 사용
        vision_load_in_8bit: Transformers 8bit 양자화 사용
        vision_batch_size: Transformers 배치 크기 (기본: 4)
        save: True면 마크다운 파일 덮어쓰기 (기본: True)

    Returns:
        업데이트된 마크다운 내용

    Example:
        >>> # 기본 사용법
        >>> updated = update_markdown_with_images(
        ...     "document.docx",
        ...     "output/document/document.md",
        ...     vision_provider="openai"
        ... )

        >>> # 폴백 순서 지정
        >>> updated = update_markdown_with_images(
        ...     "document.docx",
        ...     "output/document/document.md",
        ...     vision_provider=["gemini", "openai"]  # gemini 실패시 openai 시도
        ... )

        >>> # 저장 없이 결과만 확인
        >>> updated = update_markdown_with_images(
        ...     "document.docx",
        ...     "output/document/document.md",
        ...     save=False
        ... )
    """
    import re

    docx_path = Path(docx_path)
    markdown_path = Path(markdown_path)

    # 1. 기존 마크다운 파일 읽기
    if not markdown_path.exists():
        raise FileNotFoundError(f"마크다운 파일을 찾을 수 없습니다: {markdown_path}")

    with open(markdown_path, 'r', encoding='utf-8') as f:
        existing_content = f.read()

    # 2. [IMAGE_N] 플레이스홀더 확인 (이미 설명이 있는지 체크)
    # [IMAGE_1] 형태만 찾음 ([IMAGE_1: ...] 형태는 이미 설명이 있는 것)
    placeholder_pattern = re.compile(r'\[IMAGE_(\d+)\](?!\()')
    placeholders = placeholder_pattern.findall(existing_content)

    if not placeholders:
        # 이미 모든 이미지에 설명이 있거나 이미지가 없음
        return existing_content

    # 3. DOCX 파싱해서 이미지 정보 추출
    output_dir = markdown_path.parent
    parser = DocxParser(
        extract_images=True,
        extract_metadata=False,
        extract_tables=False,
    )
    result = parser.parse(docx_path, output_dir=output_dir)

    if not result.images_list:
        return existing_content

    # 4. Vision AI로 이미지 설명 생성
    from .vision import create_vision_provider, VisionProvider as VP

    if isinstance(vision_provider, VP):
        # 이미 VisionProvider 인스턴스인 경우
        result.describe_images(vision_provider, image_prompts=image_prompts)
    else:
        # 문자열 또는 리스트인 경우
        if isinstance(vision_provider, str):
            providers = [vision_provider]
        else:
            providers = vision_provider

        last_error = None
        described = False

        for provider_name in providers:
            try:
                provider_kwargs: Dict[str, Any] = {
                    "max_tokens": vision_max_tokens,
                }

                if vision_model:
                    provider_kwargs["model"] = vision_model

                if provider_name == "transformers":
                    provider_kwargs["load_in_4bit"] = vision_load_in_4bit
                    provider_kwargs["load_in_8bit"] = vision_load_in_8bit
                    provider_kwargs["batch_size"] = vision_batch_size

                provider = create_vision_provider(
                    provider=provider_name,
                    **provider_kwargs,
                )
                result.describe_images(provider, image_prompts=image_prompts)
                described = True
                break
            except Exception as e:
                last_error = e
                continue

        if not described and last_error:
            import warnings
            warnings.warn(f"모든 vision provider가 실패했습니다. 마지막 에러: {last_error}")
            return existing_content

    if not result.image_descriptions:
        return existing_content

    # 5. 기존 마크다운에서 [IMAGE_N] 플레이스홀더만 교체
    # 이미 경로가 있는 경우 ([IMAGE_N](path)) 는 설명만 추가
    # 경로가 없는 경우 ([IMAGE_N]) 는 설명과 경로 모두 추가
    updated_content = existing_content
    image_paths = {img.index: img.path for img in result.images_list}

    for img_num, desc in result.image_descriptions.items():
        path = image_paths.get(img_num, "")

        # 패턴 1: [IMAGE_N] (경로 없음) -> [IMAGE_N: desc](path)
        old_placeholder = f"[IMAGE_{img_num}]"
        if old_placeholder in updated_content:
            # 바로 뒤에 (path)가 없는 경우만 교체
            pattern = re.compile(rf'\[IMAGE_{img_num}\](?!\()')
            if path:
                replacement = f"[IMAGE_{img_num}: {desc}]({path})"
            else:
                replacement = f"[IMAGE_{img_num}: {desc}]"
            updated_content = pattern.sub(replacement, updated_content)

    # 6. 저장
    if save:
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

    return updated_content


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
    auto_describe_images: Union[
        bool,
        Literal["openai", "anthropic", "gemini", "google", "transformers"],
        List[Literal["openai", "anthropic", "gemini", "google", "transformers"]]
    ] = False,
    image_prompts: Optional[Dict[int, str]] = None,
    save_file: bool = False,
    convert_images: bool = True,
    heading_patterns: Optional[List[Tuple[str, int]]] = None,
    extract_tables: bool = False,
    auto_summarize_tables: Union[
        bool,
        Literal["openai", "claude", "gemini", "google", "cerebras"],
        List[Literal["openai", "claude", "gemini", "google", "cerebras"]]
    ] = False,
    summarizer_max_tokens: int = 200,
    vision_max_tokens: int = 300,
    vision_model: Optional[str] = None,
    vision_load_in_4bit: bool = False,
    vision_load_in_8bit: bool = False,
    vision_batch_size: int = 4,
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
        vision_provider: VisionProvider instance for image description (deprecated, use auto_describe_images)
        auto_describe_images: Provider(s) for image description (vision AI)
            - False: No image description (default)
            - True: Use vision_provider if provided
            - "openai": Use OpenAI API (gpt-4o)
            - "anthropic": Use Anthropic Claude API (claude-sonnet-4-20250514)
            - "gemini" or "google": Use Google Gemini API (gemini-1.5-flash)
            - "transformers": Use local Transformers model (LLaVA)
            - ["gemini", "openai", ...]: Fallback order (try first, if fails try next)
        image_prompts: Dictionary mapping image index to custom prompt
        save_file: Whether to save content file when output_dir is specified
        convert_images: Convert non-standard image formats to PNG
        heading_patterns: Custom patterns for hierarchy_mode="pattern"
        extract_tables: Whether to extract tables to separate files
        auto_summarize_tables: Provider(s) for table summarization
            - False: No summarization (default)
            - "openai": Use OpenAI API (gpt-4o-mini)
            - "claude": Use Anthropic Claude API (claude-3-5-haiku)
            - "gemini" or "google": Use Google Gemini API (gemini-2.0-flash)
            - "cerebras": Use Cerebras API (llama-3.3-70b)
            - ["cerebras", "openai", ...]: Fallback order (try first, if fails try next)
        summarizer_max_tokens: Max tokens for table summary (default: 200)
        vision_max_tokens: Max tokens for image description (default: 300)
        vision_model: Model ID for vision provider (e.g., "gpt-4o-mini", "llava-hf/llava-v1.6-mistral-7b-hf")
        vision_load_in_4bit: Use 4-bit quantization for transformers (reduces VRAM usage)
        vision_load_in_8bit: Use 8-bit quantization for transformers
        vision_batch_size: Batch size for transformers (default: 4, adjust based on VRAM)
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
        """Save result based on output_format.

        Output structure: output/{docx_stem}/{docx_stem}.md
        """
        if not out_dir:
            return
        base_name = result.source.stem if result.source else "output"
        doc_dir = out_dir / base_name
        doc_dir.mkdir(parents=True, exist_ok=True)

        if fmt == OutputFormat.MARKDOWN:
            result.save_markdown(doc_dir / f"{base_name}.md")
        elif fmt == OutputFormat.TEXT:
            result.save_text(doc_dir / f"{base_name}.txt")
        elif fmt == OutputFormat.JSON:
            result.save_json(doc_dir / f"{base_name}.json")

    def _process_result(result: ParseResult) -> None:
        """Process image and table descriptions for a result."""
        # Set year in metadata (user-specified takes priority)
        if year and result.metadata:
            result.metadata.year = year

        # Handle image descriptions (with vision AI)
        if auto_describe_images and result.images_list:
            # Normalize providers to list
            if isinstance(auto_describe_images, str):
                vision_providers = [auto_describe_images]
            elif isinstance(auto_describe_images, list):
                vision_providers = auto_describe_images
            elif auto_describe_images is True and vision_provider:
                # Backward compatibility: use provided vision_provider
                result.describe_images(vision_provider, image_prompts=image_prompts)
                vision_providers = []  # Skip provider loop
            else:
                vision_providers = []

            if vision_providers:
                from .vision import create_vision_provider

                last_error = None
                described = False

                for provider_name in vision_providers:
                    try:
                        # Build kwargs based on provider type
                        provider_kwargs = {
                            "max_tokens": vision_max_tokens,
                        }

                        # Add model if specified
                        if vision_model:
                            if provider_name == "transformers":
                                provider_kwargs["model"] = vision_model
                            else:
                                provider_kwargs["model"] = vision_model

                        # Add transformers-specific options
                        if provider_name == "transformers":
                            provider_kwargs["load_in_4bit"] = vision_load_in_4bit
                            provider_kwargs["load_in_8bit"] = vision_load_in_8bit
                            provider_kwargs["batch_size"] = vision_batch_size

                        provider = create_vision_provider(
                            provider=provider_name,
                            **provider_kwargs,
                        )
                        result.describe_images(provider, image_prompts=image_prompts)
                        described = True
                        break  # Success, stop trying
                    except Exception as e:
                        last_error = e
                        continue  # Try next provider

                if not described and last_error:
                    import warnings
                    warnings.warn(f"All vision providers failed. Last error: {last_error}")

        # Always replace image placeholders with paths (like tables)
        if result.images_list:
            result.content = result.replace_image_placeholders(result.image_descriptions)
            result.markdown_content = result.content

        # Update table data with image descriptions before summarization
        if result.image_descriptions and result.tables_list:
            import re
            for table in result.tables_list:
                if table.rows:
                    for row_idx, row in enumerate(table.rows):
                        for col_idx, cell in enumerate(row):
                            # Replace [IMAGE_N] with [IMAGE_N: description]
                            def replace_image(match):
                                num = int(match.group(1))
                                if num in result.image_descriptions:
                                    desc = result.image_descriptions[num]
                                    return f"[IMAGE_{num}: {desc}]"
                                return match.group(0)
                            table.rows[row_idx][col_idx] = re.sub(
                                r'\[IMAGE_(\d+)\]', replace_image, cell
                            )

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
                # Use longer delay for large table counts to avoid rate limits
                table_count = len(result.tables_list)
                delay = 2.0 if table_count > 50 else 0.5

                for provider in providers:
                    try:
                        summarizer = create_table_summarizer(
                            provider=provider,
                            max_tokens=summarizer_max_tokens,
                        )
                        summaries = summarizer.summarize_tables(
                            result.tables_list,
                            delay=delay,
                        )
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
