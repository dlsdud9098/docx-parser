"""
Core DOCX parser - extracts text with image placeholders and metadata.

Features:
- Text extraction with [IMAGE_N] placeholders
- DOCX metadata extraction (author, title, page count, etc.)
- Multiple output formats (markdown, text, json)
- LangChain Document compatible
"""

import zipfile
import xml.etree.ElementTree as ET
import json
import io
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Union, TYPE_CHECKING, Tuple
from enum import Enum
import re

if TYPE_CHECKING:
    from .vision.base import VisionProvider


# ============================================================================
# Image Format Detection and Conversion
# ============================================================================

# Magic bytes for image format detection
IMAGE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'png',
    b'\xff\xd8\xff': 'jpeg',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'BM': 'bmp',
    b'II*\x00': 'tiff',  # Little-endian TIFF
    b'MM\x00*': 'tiff',  # Big-endian TIFF
    b'RIFF': 'webp',     # WebP (need to check further)
    b'II\xbc\x01': 'wdp',  # JPEG XR / HD Photo / WDP
    b'\x01\x00\x00\x00': 'emf',  # EMF (simplified)
    b'\xd7\xcd\xc6\x9a': 'wmf',  # WMF
}


def detect_image_format(data: bytes) -> Optional[str]:
    """Detect image format from magic bytes.

    Args:
        data: Image binary data

    Returns:
        Format string ('png', 'jpeg', 'gif', 'wdp', 'emf', 'wmf', etc.) or None
    """
    for signature, fmt in IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            # Special check for WebP (RIFF....WEBP)
            if fmt == 'webp' and len(data) >= 12:
                if data[8:12] != b'WEBP':
                    continue
            return fmt
    return None


def _convert_wdp_to_png(data: bytes) -> Optional[bytes]:
    """Convert WDP/JPEG XR to PNG using JxrDecApp (if available).

    Args:
        data: WDP image binary data

    Returns:
        PNG data if successful, None if conversion failed
    """
    import subprocess
    import tempfile
    import shutil

    # Check if JxrDecApp is available
    if not shutil.which('JxrDecApp'):
        return None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            wdp_path = Path(tmpdir) / 'input.wdp'
            bmp_path = Path(tmpdir) / 'output.bmp'

            # Write WDP file
            with open(wdp_path, 'wb') as f:
                f.write(data)

            # Convert WDP to BMP using JxrDecApp
            result = subprocess.run(
                ['JxrDecApp', '-i', str(wdp_path), '-o', str(bmp_path)],
                capture_output=True,
                timeout=30
            )

            if result.returncode != 0 or not bmp_path.exists():
                return None

            # Convert BMP to PNG using PIL
            from PIL import Image

            img = Image.open(bmp_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()

    except Exception:
        return None


def convert_image_to_png(data: bytes, original_ext: str) -> Tuple[bytes, str]:
    """Convert image data to PNG format if needed.

    Args:
        data: Original image binary data
        original_ext: Original file extension (e.g., '.wdp', '.tmp')

    Returns:
        Tuple of (converted_data, new_extension)
        If conversion fails or not needed, returns original data with original ext
    """
    ext_lower = original_ext.lower()

    # Already PNG or common web formats - no conversion needed
    if ext_lower in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return data, original_ext

    # Detect actual format for .tmp files
    if ext_lower == '.tmp':
        detected = detect_image_format(data)
        if detected in ('png', 'jpeg', 'gif', 'webp'):
            # It's already a standard format, just fix extension
            new_ext = '.jpg' if detected == 'jpeg' else f'.{detected}'
            return data, new_ext

    # WDP/HDP (JPEG XR) - use JxrDecApp if available
    if ext_lower in ('.wdp', '.hdp', '.jxr'):
        png_data = _convert_wdp_to_png(data)
        if png_data:
            return png_data, '.png'
        # Fall through to PIL attempt

    # Convert using PIL
    from PIL import Image

    try:
        # Try to open and convert
        img = Image.open(io.BytesIO(data))

        # Convert to RGB if necessary (for RGBA or palette images)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Save as PNG
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue(), '.png'

    except Exception:
        # Conversion failed (unsupported format), return original
        return data, original_ext


def process_image(data: bytes, original_name: str, convert_to_png: bool = True) -> Tuple[bytes, str]:
    """Process image: detect format, convert if needed.

    Args:
        data: Image binary data
        original_name: Original filename
        convert_to_png: Whether to convert non-standard formats to PNG

    Returns:
        Tuple of (processed_data, new_filename)
    """
    original_path = Path(original_name)
    original_ext = original_path.suffix.lower()
    stem = original_path.stem

    if not convert_to_png:
        return data, original_name

    # Convert if needed
    new_data, new_ext = convert_image_to_png(data, original_ext)

    if new_ext != original_ext:
        new_name = stem + new_ext
        return new_data, new_name

    return data, original_name


# ============================================================================
# Circled Number Conversion
# ============================================================================

# Circled numbers mapping: ① -> 1, ② -> 2, etc.
CIRCLED_NUMBERS = {
    '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
    '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
    '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
    '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20,
    '㉑': 21, '㉒': 22, '㉓': 23, '㉔': 24, '㉕': 25,
    '㉖': 26, '㉗': 27, '㉘': 28, '㉙': 29, '㉚': 30,
    '㉛': 31, '㉜': 32, '㉝': 33, '㉞': 34, '㉟': 35,
}

# Pattern to match circled numbers at the start of a line
CIRCLED_NUMBER_PATTERN = re.compile(r'^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s*(.*)$')


def convert_circled_numbers(content: str, indent: str = "   ") -> str:
    """Convert circled numbers (①②③) to numbered list format with indentation.

    Args:
        content: Text content with circled numbers
        indent: Indentation string for content under numbered items (default: 3 spaces)

    Returns:
        Converted text with numbered list format

    Example:
        Input:
            ① First item

            Some content

            ② Second item

            Content here

        Output:
            1. First item

               Some content

            2. Second item

               Content here
    """
    lines = content.split('\n')
    result = []
    in_numbered_section = False
    empty_line_count = 0

    # Patterns that indicate end of numbered section
    section_end_patterns = [
        r'^\(\d+\)',       # (1), (2), etc.
        r'^#+ ',           # Markdown headings
        r'^\|',            # Table rows
        r'^---',           # Horizontal rules
        r'^\[\w+\]',       # Image placeholders or links at start
    ]
    section_end_re = re.compile('|'.join(section_end_patterns))

    for line in lines:
        stripped = line.strip()

        # Check if line starts with circled number
        match = CIRCLED_NUMBER_PATTERN.match(stripped)
        if match:
            circled = match.group(1)
            rest = match.group(2)
            num = CIRCLED_NUMBERS.get(circled, 0)
            if num:
                result.append(f"{num}. {rest}")
                in_numbered_section = True
                empty_line_count = 0
                continue

        # Check if this line ends the numbered section
        if in_numbered_section and stripped:
            # Check for section-ending patterns
            if section_end_re.match(stripped):
                in_numbered_section = False
            # Check for too many consecutive empty lines (section break)
            elif empty_line_count >= 3:
                in_numbered_section = False
                empty_line_count = 0

        # Track empty lines
        if not stripped:
            empty_line_count += 1
        else:
            empty_line_count = 0

        # If we're in a numbered section (after a circled number)
        if in_numbered_section:
            if stripped:
                # Non-empty line: add indentation
                result.append(f"{indent}{stripped}")
            else:
                # Empty line: keep as is (maintains spacing)
                result.append(line)
        else:
            # Not in numbered section
            result.append(line)

    return '\n'.join(result)


class VerticalMergeMode(str, Enum):
    """How to handle vertically merged cells"""
    REPEAT = "repeat"      # Repeat the value in merged cells
    EMPTY = "empty"        # Keep merged cells empty
    FIRST_ONLY = "first"   # Only show value in first cell


class HorizontalMergeMode(str, Enum):
    """How to handle horizontally merged cells"""
    EXPAND = "expand"      # Expand to multiple empty cells
    SINGLE = "single"      # Keep as single cell (ignore span)
    REPEAT = "repeat"      # Repeat value in spanned cells


class OutputFormat(str, Enum):
    """Output format for parsed content"""
    MARKDOWN = "markdown"  # Default: Markdown format with tables
    TEXT = "text"          # Plain text (no markdown formatting)
    JSON = "json"          # Structured JSON output


class HierarchyMode(str, Enum):
    """How to detect heading hierarchy"""
    NONE = "none"            # No heading detection (default, backward compatible)
    AUTO = "auto"            # Style first, font_size fallback
    STYLE = "style"          # Use styles.xml outlineLevel only
    FONT_SIZE = "font_size"  # Use font size only
    PATTERN = "pattern"      # Use custom text patterns (e.g., "I. ", "1. ", "1)")


# Type alias for heading patterns: list of (pattern, header_level)
# Example: [("I. ", 1), ("1. ", 2), ("1)", 3), ("(1)", 4)]
HeadingPattern = List[Tuple[str, int]]


class TableFormat(str, Enum):
    """Output format for tables"""
    MARKDOWN = "markdown"    # Markdown table (default)
    JSON = "json"            # Structured JSON with merge info
    HTML = "html"            # HTML table with colspan/rowspan
    TEXT = "text"            # Tab-separated text


class BlockType(str, Enum):
    """Content block types for structured JSON output"""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"


# ============================================================================
# Content Block Data Classes
# ============================================================================

@dataclass
class ParagraphBlock:
    """Paragraph content block"""
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": BlockType.PARAGRAPH.value,
            "content": self.content
        }


@dataclass
class HeadingBlock:
    """Heading content block"""
    content: str
    level: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": BlockType.HEADING.value,
            "level": self.level,
            "content": self.content
        }


@dataclass
class TableBlock:
    """Table content block"""
    rows: List[List[str]]
    headers: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
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
    """Image content block"""
    index: int
    path: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": BlockType.IMAGE.value,
            "index": self.index
        }
        if self.path:
            result["path"] = self.path
        if self.description:
            result["description"] = self.description
        return result


# ============================================================================
# Metadata Data Classes
# ============================================================================

@dataclass
class CoreMetadata:
    """Dublin Core metadata from docProps/core.xml"""
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None          # author
    keywords: Optional[str] = None
    description: Optional[str] = None
    last_modified_by: Optional[str] = None
    revision: Optional[int] = None
    created: Optional[str] = None          # ISO 8601 datetime
    modified: Optional[str] = None         # ISO 8601 datetime


@dataclass
class AppMetadata:
    """Application metadata from docProps/app.xml"""
    template: Optional[str] = None
    total_time: Optional[int] = None       # editing time in minutes
    pages: Optional[int] = None
    words: Optional[int] = None
    characters: Optional[int] = None
    characters_with_spaces: Optional[int] = None
    lines: Optional[int] = None
    paragraphs: Optional[int] = None
    application: Optional[str] = None
    app_version: Optional[str] = None
    company: Optional[str] = None


@dataclass
class DocxMetadata:
    """Combined DOCX metadata"""
    core: CoreMetadata = field(default_factory=CoreMetadata)
    app: AppMetadata = field(default_factory=AppMetadata)
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None        # bytes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for LangChain metadata"""
        result = {}
        # Core metadata
        if self.core:
            if self.core.title:
                result["title"] = self.core.title
            if self.core.subject:
                result["subject"] = self.core.subject
            if self.core.creator:
                result["author"] = self.core.creator
            if self.core.keywords:
                result["keywords"] = self.core.keywords
            if self.core.description:
                result["description"] = self.core.description
            if self.core.last_modified_by:
                result["last_modified_by"] = self.core.last_modified_by
            if self.core.revision:
                result["revision"] = self.core.revision
            if self.core.created:
                result["created_date"] = self.core.created
            if self.core.modified:
                result["modified_date"] = self.core.modified
        # App metadata
        if self.app:
            if self.app.pages:
                result["total_pages"] = self.app.pages
            if self.app.words:
                result["word_count"] = self.app.words
            if self.app.characters:
                result["character_count"] = self.app.characters
            if self.app.paragraphs:
                result["paragraph_count"] = self.app.paragraphs
            if self.app.lines:
                result["line_count"] = self.app.lines
            if self.app.application:
                result["application"] = self.app.application
            if self.app.app_version:
                result["app_version"] = self.app.app_version
            if self.app.company:
                result["company"] = self.app.company
        # File info
        if self.file_path:
            result["file_path"] = self.file_path
        if self.file_name:
            result["file_name"] = self.file_name
        if self.file_size:
            result["file_size"] = self.file_size
        return result


@dataclass
class ImageInfo:
    """Image information with improved structure"""
    index: int
    name: str
    path: Optional[str] = None
    original_name: Optional[str] = None
    data: Optional[bytes] = None  # 이미지 바이너리 데이터 (메모리 내 처리용)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "index": self.index,
            "name": self.name,
            "path": self.path,
            "original_name": self.original_name
        }


@dataclass
class StyleInfo:
    """Style information from styles.xml for heading detection"""
    style_id: str
    name: Optional[str] = None
    outline_level: Optional[int] = None  # 0=H1, 1=H2, ..., 8=H9
    font_size: Optional[int] = None      # half-points (24 = 12pt)


@dataclass
class TableCell:
    """Represents a table cell with merge information"""
    text: str
    colspan: int = 1
    rowspan: int = 1
    is_header: bool = False
    is_merged_continuation: bool = False  # True if this cell continues a merge

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {"text": self.text}
        if self.colspan > 1:
            result["colspan"] = self.colspan
        if self.rowspan > 1:
            result["rowspan"] = self.rowspan
        if self.is_header:
            result["is_header"] = True
        return result


@dataclass
class TableData:
    """Structured table data"""
    rows: List[List[TableCell]]
    col_count: int = 0
    row_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": "table",
            "rows": [
                {"cells": [cell.to_dict() for cell in row]}
                for row in self.rows
            ],
            "col_count": self.col_count,
            "row_count": self.row_count
        }


@dataclass
class ParseResult:
    """Result of parsing a DOCX file"""
    content: Union[str, List[Dict[str, Any]]]  # String (markdown/text) or List of blocks (json)
    images: Dict[int, Path] = field(default_factory=dict)  # {num: image_path} - backward compat
    image_mapping: Dict[int, str] = field(default_factory=dict)  # {num: filename} - backward compat
    source: Optional[Path] = None
    image_count: int = 0
    # New fields for enhanced functionality
    metadata: Optional[DocxMetadata] = None
    images_list: List[ImageInfo] = field(default_factory=list)  # Improved image structure
    output_format: OutputFormat = OutputFormat.MARKDOWN
    text_content: Optional[str] = None  # Plain text version (always available)
    markdown_content: Optional[str] = None  # Markdown version (always available)
    # Vision-generated image descriptions
    image_descriptions: Dict[int, str] = field(default_factory=dict)

    def save_markdown(self, path: str | Path) -> Path:
        """Save content to markdown file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use markdown_content if content is blocks (JSON mode)
        content = self.markdown_content if self.markdown_content else self.content
        if isinstance(content, list):
            content = self.markdown_content or ""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def save_text(self, path: str | Path) -> Path:
        """Save plain text content to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.text_content if self.text_content else self.content
        if isinstance(content, list):
            content = self.text_content or ""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def save_json(self, path: str | Path) -> Path:
        """Save structured JSON to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        return path

    def save_mapping(self, path: str | Path) -> Path:
        """Save image mapping to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for num, filename in sorted(self.image_mapping.items()):
                f.write(f"[IMAGE_{num}] -> {filename}\n")
        return path

    def get_image_path(self, num: int) -> Optional[Path]:
        """Get image path by number"""
        return self.images.get(num)

    def replace_placeholders(self, descriptions: Dict[int, str]) -> str:
        """Replace [IMAGE_N] placeholders with image link and descriptions.

        Output format:
            ![IMAGE_N](path/to/image.png)

            설명 텍스트...
        """
        content = self.content

        # 이미지 인덱스 -> 경로 매핑
        image_paths = {img.index: img.path for img in self.images_list}

        for num, desc in descriptions.items():
            path = image_paths.get(num)
            if path:
                # 마크다운 이미지 링크 + 설명
                replacement = f"\n\n![IMAGE_{num}]({path})\n\n{desc}\n\n"
            else:
                # 경로 없으면 설명만
                replacement = f"\n\n[Image: {desc}]\n\n"
            content = content.replace(f"[IMAGE_{num}]", replacement)

        return content

    def describe_images(
        self,
        provider: "VisionProvider",
        force: bool = False,
        image_prompts: Optional[Dict[int, str]] = None,
    ) -> Dict[int, str]:
        """Vision provider를 사용하여 이미지 설명 생성

        Args:
            provider: VisionProvider 인스턴스
            force: True이면 기존 설명 덮어쓰기
            image_prompts: {이미지_인덱스: 프롬프트} 매핑 (선택)
                - 이미지별로 다른 프롬프트를 사용할 수 있음
                - 예: {1: "도면 분석 프롬프트", 2: "차트 분석 프롬프트"}

        Returns:
            {이미지_인덱스: 설명} 딕셔너리

        Example:
            from docx_parser.vision import create_vision_provider

            provider = create_vision_provider("openai")

            # 기본 사용
            descriptions = result.describe_images(provider)

            # 이미지별 다른 프롬프트 사용
            descriptions = result.describe_images(provider, image_prompts={
                1: "이 기술 도면을 상세히 분석해주세요...",
                2: "이 차트의 트렌드를 설명해주세요...",
            })
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

    def get_described_content(
        self,
        provider: Optional["VisionProvider"] = None,
        descriptions: Optional[Dict[int, str]] = None,
    ) -> str:
        """이미지 설명이 포함된 콘텐츠 반환

        Args:
            provider: VisionProvider (새로 설명 생성 시)
            descriptions: 직접 제공하는 설명 딕셔너리

        Returns:
            [IMAGE_N]이 [Image: 설명]으로 대체된 콘텐츠

        Example:
            # 방법 1: 미리 생성된 설명 사용
            result.describe_images(provider)
            content = result.get_described_content()

            # 방법 2: provider를 전달하여 한 번에 처리
            content = result.get_described_content(provider=provider)

            # 방법 3: 직접 설명 딕셔너리 제공
            content = result.get_described_content(descriptions={1: "로고", 2: "차트"})
        """
        if descriptions:
            return self.replace_placeholders(descriptions)

        if provider:
            descs = self.describe_images(provider)
            return self.replace_placeholders(descs)

        if self.image_descriptions:
            return self.replace_placeholders(self.image_descriptions)

        return self.content

    def to_json(self) -> str:
        """Convert ParseResult to JSON string"""
        # If content is already blocks (JSON mode), use it directly
        if isinstance(self.content, list):
            content_data = self.content
        else:
            content_data = self.text_content or self.content

        data = {
            "content": content_data,
            "image_count": self.image_count,
            "images": [img.to_dict() for img in self.images_list],
            "source": str(self.source) if self.source else None,
            "metadata": self.metadata.to_dict() if self.metadata else {}
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def to_langchain_metadata(self) -> Dict[str, Any]:
        """Generate LangChain-compatible metadata dictionary"""
        meta = {
            "source": str(self.source) if self.source else None,
            "page": 1,  # DOCX is treated as single document
            "file_type": "docx",
            "image_count": self.image_count,
        }
        # Add DOCX metadata
        if self.metadata:
            meta.update(self.metadata.to_dict())
        # Add images list
        if self.images_list:
            meta["images"] = [img.to_dict() for img in self.images_list]
        # Keep backward compatibility
        if self.image_mapping:
            meta["image_mapping"] = self.image_mapping
        return meta

    def to_langchain_documents(
        self,
        described: bool = False,
        provider: Optional["VisionProvider"] = None,
    ) -> List[Any]:
        """Convert ParseResult to LangChain Document list.

        Similar to LlamaParse's get_markdown_documents() / get_text_documents().

        Args:
            described: If True, use content with image descriptions
            provider: VisionProvider to generate descriptions (optional)

        Returns:
            List[Document] - LangChain Document list

        Example:
            from docx_parser import parse_docx

            result = parse_docx("document.docx")

            # Basic usage
            docs = result.to_langchain_documents()

            # With image descriptions
            from docx_parser.vision import create_vision_provider
            provider = create_vision_provider("openai")
            docs = result.to_langchain_documents(described=True, provider=provider)

            # Use with LangChain
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
            chunks = splitter.split_documents(docs)

        Raises:
            ImportError: If langchain is not installed
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
            described: If True, use content with image descriptions
            provider: VisionProvider to generate descriptions (optional)

        Returns:
            List[Document] - LlamaIndex Document list

        Example:
            from docx_parser import parse_docx

            result = parse_docx("document.docx")

            # Basic usage
            docs = result.to_llama_index_documents()

            # Use with LlamaIndex
            from llama_index.core import VectorStoreIndex
            index = VectorStoreIndex.from_documents(docs)

        Raises:
            ImportError: If llama-index is not installed
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

        metadata = self.to_langchain_metadata()

        return [Document(text=content, metadata=metadata)]


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

    With output format:
        parser = DocxParser(output_format="text")
        result = parser.parse("document.docx")
        print(result.content)  # Plain text without markdown
    """

    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    }

    METADATA_NAMESPACES = {
        'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
        'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
    }

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
        convert_circled_numbers: bool = True,
        heading_patterns: Optional[List[Tuple[str, int]]] = None,
    ):
        """
        Initialize parser.

        Args:
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
                - "pattern": Use custom text patterns
            max_heading_level: Maximum heading depth (1-6, default: 6)
            table_format: Output format for tables
                - "markdown": Markdown table format (default)
                - "json": Structured JSON with merge info preserved
                - "html": HTML table with colspan/rowspan
                - "text": Tab-separated plain text
            convert_images: Convert non-standard formats (WDP, TMP, EMF) to PNG (default: True)
            convert_circled_numbers: Convert ①②③ to numbered list format (default: True)
            heading_patterns: Custom patterns for hierarchy_mode="pattern"
                List of (pattern, level) tuples. Pattern can be:
                - Literal string: "I. ", "1. ", "1)", "(1)"
                - Regex pattern starting with ^: "^[IVX]+\\. ", "^\\d+\\. "
                Example: [("I. ", 1), ("1. ", 2), ("1)", 3), ("(1)", 4)]
        """
        self.extract_images = extract_images
        self.image_placeholder = image_placeholder
        self.vertical_merge = VerticalMergeMode(vertical_merge)
        self.horizontal_merge = HorizontalMergeMode(horizontal_merge)
        self.output_format = OutputFormat(output_format)
        self.convert_images = convert_images
        self.extract_metadata = extract_metadata
        self.hierarchy_mode = HierarchyMode(hierarchy_mode)
        self.max_heading_level = min(max(1, max_heading_level), 6)
        self.table_format = TableFormat(table_format)
        self.convert_circled_numbers = convert_circled_numbers
        self.heading_patterns = self._compile_heading_patterns(heading_patterns)

    def parse(
        self,
        docx_path: str | Path,
        output_dir: Optional[str | Path] = None
    ) -> ParseResult:
        """
        Parse DOCX file.

        Args:
            docx_path: Path to DOCX file
            output_dir: Directory to save images (optional)

        Returns:
            ParseResult with content, image information, and metadata
        """
        docx_path = Path(docx_path)

        if output_dir:
            output_dir = Path(output_dir)
            img_dir = output_dir / "images" / docx_path.stem
            img_dir.mkdir(parents=True, exist_ok=True)
        else:
            img_dir = None

        with zipfile.ZipFile(docx_path, 'r') as z:
            # Extract metadata if requested
            metadata = None
            if self.extract_metadata:
                metadata = self._extract_metadata(z, docx_path)

            # Extract image mapping from relationships
            rid_to_file = self._parse_relationships(z)

            # Create numbered mapping
            img_files = sorted(set(rid_to_file.values()))
            file_to_num = {f: i+1 for i, f in enumerate(img_files)}
            rid_to_num = {rid: file_to_num[f] for rid, f in rid_to_file.items()}

            # Extract images if requested
            images = {}
            image_mapping = {}
            images_list = []

            if self.extract_images:
                for img_name in img_files:
                    num = file_to_num[img_name]
                    try:
                        img_data = z.read(f"word/media/{img_name}")

                        # Convert image if needed (WDP, TMP, EMF -> PNG)
                        if self.convert_images:
                            img_data, converted_name = process_image(
                                img_data, img_name, convert_to_png=True
                            )
                        else:
                            converted_name = img_name

                        new_name = f"{num:03d}_{converted_name}"

                        if img_dir:
                            # 파일로 저장
                            img_path = img_dir / new_name
                            with open(img_path, 'wb') as f:
                                f.write(img_data)
                            images[num] = img_path
                            image_mapping[num] = new_name
                            images_list.append(ImageInfo(
                                index=num,
                                name=new_name,
                                path=str(img_path),
                                original_name=img_name,
                                data=img_data,  # bytes도 저장 (Vision용)
                            ))
                        else:
                            # 메모리에만 저장 (output_dir 없을 때)
                            image_mapping[num] = converted_name
                            images_list.append(ImageInfo(
                                index=num,
                                name=converted_name,
                                path=None,
                                original_name=img_name,
                                data=img_data,  # bytes 저장 (Vision용)
                            ))
                    except KeyError:
                        pass
            else:
                for img_name in img_files:
                    num = file_to_num[img_name]
                    image_mapping[num] = img_name
                    images_list.append(ImageInfo(
                        index=num,
                        name=img_name,
                        path=None,
                        original_name=img_name,
                        data=None,  # extract_images=False면 data도 없음
                    ))

            # Parse document content
            doc_xml = z.read("word/document.xml").decode('utf-8')

            # Load styles and build hierarchy if needed
            styles: Dict[str, StyleInfo] = {}
            font_size_hierarchy: Dict[int, int] = {}

            if self.hierarchy_mode != HierarchyMode.NONE:
                styles = self._load_styles_info(z)

                if self.hierarchy_mode in (HierarchyMode.AUTO, HierarchyMode.FONT_SIZE):
                    font_sizes = self._collect_font_sizes(doc_xml, styles)
                    body_size = self._get_most_common_font_size(doc_xml, styles)
                    font_size_hierarchy = self._build_font_size_hierarchy(font_sizes, body_size)

        # Parse content as markdown
        markdown_content = self._parse_content(doc_xml, rid_to_num, styles, font_size_hierarchy)

        # Convert to plain text
        text_content = self._to_text(markdown_content)

        # Determine final content based on output format
        if self.output_format == OutputFormat.TEXT:
            content = text_content
        elif self.output_format == OutputFormat.JSON:
            # Parse as structured blocks for JSON output
            content = self._parse_content_blocks(doc_xml, rid_to_num, styles, font_size_hierarchy)
        else:
            content = markdown_content

        return ParseResult(
            content=content,
            images=images,
            image_mapping=image_mapping,
            source=docx_path,
            image_count=len(img_files),
            metadata=metadata,
            images_list=images_list,
            output_format=self.output_format,
            text_content=text_content,
            markdown_content=markdown_content,
        )

    # ========================================================================
    # Metadata Extraction Methods
    # ========================================================================

    def _extract_metadata(self, z: zipfile.ZipFile, docx_path: Path) -> DocxMetadata:
        """Extract all metadata from DOCX file"""
        return DocxMetadata(
            core=self._extract_core_metadata(z),
            app=self._extract_app_metadata(z),
            file_path=str(docx_path.absolute()),
            file_name=docx_path.name,
            file_size=docx_path.stat().st_size if docx_path.exists() else None,
        )

    def _extract_core_metadata(self, z: zipfile.ZipFile) -> CoreMetadata:
        """Extract metadata from docProps/core.xml (Dublin Core)"""
        try:
            core_xml = z.read("docProps/core.xml").decode('utf-8')
        except KeyError:
            return CoreMetadata()

        root = ET.fromstring(core_xml)
        ns = self.METADATA_NAMESPACES

        def get_text(xpath: str) -> Optional[str]:
            elem = root.find(xpath, ns)
            return elem.text.strip() if elem is not None and elem.text else None

        def get_int(xpath: str) -> Optional[int]:
            text = get_text(xpath)
            if text and text.isdigit():
                return int(text)
            return None

        return CoreMetadata(
            title=get_text('.//dc:title'),
            subject=get_text('.//dc:subject'),
            creator=get_text('.//dc:creator'),
            keywords=get_text('.//cp:keywords'),
            description=get_text('.//dc:description'),
            last_modified_by=get_text('.//cp:lastModifiedBy'),
            revision=get_int('.//cp:revision'),
            created=get_text('.//dcterms:created'),
            modified=get_text('.//dcterms:modified'),
        )

    def _extract_app_metadata(self, z: zipfile.ZipFile) -> AppMetadata:
        """Extract metadata from docProps/app.xml (Application properties)"""
        try:
            app_xml = z.read("docProps/app.xml").decode('utf-8')
        except KeyError:
            return AppMetadata()

        root = ET.fromstring(app_xml)
        # app.xml uses default namespace or no namespace
        ns = {'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'}

        def get_text(tag: str) -> Optional[str]:
            # Try with namespace first, then without
            elem = root.find(f'.//ep:{tag}', ns)
            if elem is None:
                elem = root.find(f'.//{tag}')
            return elem.text.strip() if elem is not None and elem.text else None

        def get_int(tag: str) -> Optional[int]:
            text = get_text(tag)
            if text and text.isdigit():
                return int(text)
            return None

        return AppMetadata(
            template=get_text('Template'),
            total_time=get_int('TotalTime'),
            pages=get_int('Pages'),
            words=get_int('Words'),
            characters=get_int('Characters'),
            characters_with_spaces=get_int('CharactersWithSpaces'),
            lines=get_int('Lines'),
            paragraphs=get_int('Paragraphs'),
            application=get_text('Application'),
            app_version=get_text('AppVersion'),
            company=get_text('Company'),
        )

    # ========================================================================
    # Hierarchy Detection Methods
    # ========================================================================

    def _load_styles_info(self, z: zipfile.ZipFile) -> Dict[str, StyleInfo]:
        """
        Parse styles.xml and extract style information for heading detection.

        Returns:
            Dict mapping style_id to StyleInfo
        """
        try:
            styles_xml = z.read("word/styles.xml").decode('utf-8')
        except KeyError:
            return {}

        root = ET.fromstring(styles_xml)
        ns = self.NAMESPACES
        w_ns = f"{{{ns['w']}}}"
        styles: Dict[str, StyleInfo] = {}

        for style_elem in root.findall(f'.//{w_ns}style', ns):
            style_id = style_elem.get(f'{w_ns}styleId')
            if not style_id:
                continue

            # Get style name
            name_elem = style_elem.find(f'{w_ns}name', ns)
            name = name_elem.get(f'{w_ns}val') if name_elem is not None else None

            # Get outline level (heading level)
            outline_lvl = None
            outline_elem = style_elem.find(f'.//{w_ns}outlineLvl', ns)
            if outline_elem is not None:
                val = outline_elem.get(f'{w_ns}val')
                if val and val.isdigit():
                    outline_lvl = int(val)  # 0=H1, 1=H2, ...

            # Get default font size
            font_size = None
            sz_elem = style_elem.find(f'.//{w_ns}sz', ns)
            if sz_elem is not None:
                val = sz_elem.get(f'{w_ns}val')
                if val and val.isdigit():
                    font_size = int(val)  # half-points

            styles[style_id] = StyleInfo(
                style_id=style_id,
                name=name,
                outline_level=outline_lvl,
                font_size=font_size
            )

        return styles

    def _get_paragraph_font_size(
        self,
        elem: ET.Element,
        styles: Dict[str, StyleInfo]
    ) -> Optional[int]:
        """
        Get the representative font size for a paragraph.

        Priority:
        1. First run's font size (w:r/w:rPr/w:sz)
        2. Paragraph-level font size (w:pPr/w:rPr/w:sz)
        3. Style's default font size

        Returns:
            Font size in half-points, or None if not found
        """
        ns = self.NAMESPACES
        w_ns = f"{{{ns['w']}}}"

        # 1. Check first run's font size
        for run in elem.findall(f'{w_ns}r', ns):
            rPr = run.find(f'{w_ns}rPr', ns)
            if rPr is not None:
                sz = rPr.find(f'{w_ns}sz', ns)
                if sz is not None:
                    val = sz.get(f'{w_ns}val')
                    if val and val.isdigit():
                        return int(val)
            break  # Only check first run

        # 2. Check paragraph-level font size
        pPr = elem.find(f'{w_ns}pPr', ns)
        if pPr is not None:
            rPr = pPr.find(f'{w_ns}rPr', ns)
            if rPr is not None:
                sz = rPr.find(f'{w_ns}sz', ns)
                if sz is not None:
                    val = sz.get(f'{w_ns}val')
                    if val and val.isdigit():
                        return int(val)

            # 3. Check style's default font size
            pStyle = pPr.find(f'{w_ns}pStyle', ns)
            if pStyle is not None:
                style_id = pStyle.get(f'{w_ns}val')
                if style_id and style_id in styles:
                    return styles[style_id].font_size

        return None

    def _collect_font_sizes(
        self,
        doc_xml: str,
        styles: Dict[str, StyleInfo]
    ) -> set:
        """
        Collect all unique font sizes from paragraphs.

        Returns:
            Set of unique font sizes (in half-points)
        """
        ns = self.NAMESPACES
        root = ET.fromstring(doc_xml)
        font_sizes = set()

        for para in root.findall(f'.//{{{ns["w"]}}}p', ns):
            size = self._get_paragraph_font_size(para, styles)
            if size:
                font_sizes.add(size)

        return font_sizes

    def _get_most_common_font_size(
        self,
        doc_xml: str,
        styles: Dict[str, StyleInfo]
    ) -> Optional[int]:
        """
        Find the most frequently used font size (= body text size).

        Returns:
            Most common font size in half-points, or None
        """
        from collections import Counter

        ns = self.NAMESPACES
        root = ET.fromstring(doc_xml)
        sizes = []

        for para in root.findall(f'.//{{{ns["w"]}}}p', ns):
            size = self._get_paragraph_font_size(para, styles)
            if size:
                sizes.append(size)

        if not sizes:
            return None

        counter = Counter(sizes)
        return counter.most_common(1)[0][0]

    def _build_font_size_hierarchy(
        self,
        font_sizes: set,
        body_font_size: Optional[int]
    ) -> Dict[int, int]:
        """
        Map font sizes to heading levels.
        Only font sizes larger than body_font_size become headings.

        Args:
            font_sizes: Set of all font sizes in document
            body_font_size: Most common font size (body text)

        Returns:
            Dict mapping font_size (half-points) to heading level (1-6)

        Example:
            font_sizes = {48, 36, 28, 24, 20}
            body_font_size = 24

            Result: {48: 1, 36: 2, 28: 3}
            (24 and 20 are not headings - they're body text or smaller)
        """
        if not font_sizes or body_font_size is None:
            return {}

        # Only sizes larger than body text can be headings
        larger_sizes = [s for s in font_sizes if s > body_font_size]
        sorted_sizes = sorted(larger_sizes, reverse=True)

        hierarchy = {}
        for level, size in enumerate(sorted_sizes[:self.max_heading_level], start=1):
            hierarchy[size] = level

        return hierarchy

    def _compile_heading_patterns(
        self,
        patterns: Optional[List[Tuple[str, int]]]
    ) -> Optional[List[Tuple[re.Pattern, int]]]:
        """
        Compile heading patterns to regex patterns.

        User-friendly patterns are automatically converted:
            "I. " → matches I. II. III. IV. (Roman numerals)
            "Ⅰ. " → matches Ⅰ. Ⅱ. Ⅲ. (Fullwidth Roman numerals)
            "1. " → matches 1. 2. 3. (Numbers with dot)
            "1) " → matches 1) 2) 3) (Numbers with paren)
            "(1) " → matches (1) (2) (3) (Parenthesized numbers)
            "A. " → matches A. B. C. (Uppercase letters)
            "a. " → matches a. b. c. (Lowercase letters)
            "가. " → matches 가. 나. 다. (Korean letters)

        Args:
            patterns: List of (pattern_string, heading_level) tuples
                Examples: [("I. ", 1), ("1. ", 2), ("1) ", 3), ("(1) ", 4)]

        Returns:
            List of (compiled_regex, heading_level) tuples
        """
        if not patterns:
            return None

        compiled = []
        for pattern_str, level in patterns:
            regex_pattern = self._convert_to_regex(pattern_str)

            try:
                compiled.append((re.compile(regex_pattern), level))
            except re.error as e:
                raise ValueError(f"Invalid heading pattern '{pattern_str}': {e}")

        return compiled

    def _convert_to_regex(self, pattern: str) -> str:
        """
        Convert user-friendly pattern to regex.

        Examples:
            "I. " → "^[IVXLCDMivxlcdm]+\\. "
            "Ⅰ. " → "^[Ⅰ-Ⅻⅰ-ⅻ]+\\. "
            "1. " → "^\\d+\\. "
            "1) " → "^\\d+\\) "
            "(1) " → "^\\(\\d+\\) "
            "A. " → "^[A-Z]+\\. "
            "a) " → "^[a-z]+\\) "
        """
        # If already a regex (starts with ^), return as-is
        if pattern.startswith('^'):
            return pattern

        # Define pattern templates
        conversions = [
            # Roman numerals (half-width): I. II. III.
            (r'^[IVXLCDMivxlcdm]+\. $', r'^[IVXLCDMivxlcdm]+\. '),
            (r'^[IVXLCDMivxlcdm]+\.$', r'^[IVXLCDMivxlcdm]+\.'),
            # Roman numerals (full-width): Ⅰ. Ⅱ. Ⅲ.
            (r'^[Ⅰ-Ⅻⅰ-ⅻ]+\. $', r'^[Ⅰ-Ⅻⅰ-ⅻ]+\. '),
            (r'^[Ⅰ-Ⅻⅰ-ⅻ]+\.$', r'^[Ⅰ-Ⅻⅰ-ⅻ]+\.'),
            # Numbers with dot: 1. 2. 3.
            (r'^\d+\. $', r'^\d+\. '),
            (r'^\d+\.$', r'^\d+\.'),
            # Numbers with paren: 1) 2) 3)
            (r'^\d+\) $', r'^\d+\) '),
            (r'^\d+\)$', r'^\d+\)'),
            # Parenthesized numbers: (1) (2) (3)
            (r'^\(\d+\) $', r'^\(\d+\) '),
            (r'^\(\d+\)$', r'^\(\d+\)'),
            # Uppercase letters: A. B. C.
            (r'^[A-Z]+\. $', r'^[A-Z]+\. '),
            (r'^[A-Z]+\.$', r'^[A-Z]+\.'),
            # Lowercase letters with dot: a. b. c.
            (r'^[a-z]+\. $', r'^[a-z]+\. '),
            (r'^[a-z]+\.$', r'^[a-z]+\.'),
            # Lowercase letters with paren: a) b) c)
            (r'^[a-z]+\) $', r'^[a-z]+\) '),
            (r'^[a-z]+\)$', r'^[a-z]+\)'),
            # Korean consonants: 가. 나. 다.
            (r'^[가-힣]\. $', r'^[가-힣]\. '),
            (r'^[가-힣]\.$', r'^[가-힣]\.'),
        ]

        # Check if pattern matches any known template
        for template_check, template_regex in conversions:
            if re.match(template_check, pattern):
                return template_regex

        # Fallback: escape and add ^ for line start
        escaped = re.escape(pattern)
        return f'^{escaped}'

    def _get_heading_level_by_pattern(self, text: str) -> Optional[int]:
        """
        Determine heading level based on text patterns.

        Args:
            text: Paragraph text to check

        Returns:
            Heading level (1-6) or None if no pattern matches
        """
        if not self.heading_patterns or not text:
            return None

        text_stripped = text.strip()
        if not text_stripped:
            return None

        for pattern, level in self.heading_patterns:
            if pattern.match(text_stripped):
                if 1 <= level <= self.max_heading_level:
                    return level

        return None

    def _get_heading_level(
        self,
        elem: ET.Element,
        styles: Dict[str, StyleInfo],
        font_size_hierarchy: Dict[int, int]
    ) -> Optional[int]:
        """
        Determine heading level for a paragraph based on hierarchy_mode.

        Returns:
            Heading level (1-6) or None if not a heading
        """
        ns = self.NAMESPACES
        w_ns = f"{{{ns['w']}}}"

        pPr = elem.find(f'{w_ns}pPr', ns)
        style_id = None

        if pPr is not None:
            pStyle = pPr.find(f'{w_ns}pStyle', ns)
            if pStyle is not None:
                style_id = pStyle.get(f'{w_ns}val')

        # Try style-based detection
        if self.hierarchy_mode in (HierarchyMode.STYLE, HierarchyMode.AUTO):
            if style_id and style_id in styles:
                outline_level = styles[style_id].outline_level
                if outline_level is not None:
                    # outlineLevel: 0=H1, 1=H2, ..., convert to 1-based
                    level = outline_level + 1
                    if 1 <= level <= self.max_heading_level:
                        return level

        # Try font-size-based detection
        if self.hierarchy_mode in (HierarchyMode.FONT_SIZE, HierarchyMode.AUTO):
            font_size = self._get_paragraph_font_size(elem, styles)
            if font_size and font_size in font_size_hierarchy:
                return font_size_hierarchy[font_size]

        return None

    # ========================================================================
    # Output Format Conversion Methods
    # ========================================================================

    def _to_text(self, markdown_content: str) -> str:
        """Convert markdown to plain text"""
        text = markdown_content
        # Remove markdown table formatting
        text = re.sub(r'\|', ' ', text)
        text = re.sub(r'-{3,}', '', text)
        # Remove escaped characters
        text = re.sub(r'\\([|*_`\\])', r'\1', text)
        # Remove <br> tags
        text = re.sub(r'<br>', '\n', text)
        # Clean up extra whitespace
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    # ========================================================================
    # Relationship and Content Parsing Methods
    # ========================================================================

    def _parse_relationships(self, z: zipfile.ZipFile) -> Dict[str, str]:
        """Parse document.xml.rels to get rId -> image filename mapping"""
        try:
            rels = z.read("word/_rels/document.xml.rels").decode('utf-8')
        except KeyError:
            return {}

        rid_to_file = {}
        for match in re.finditer(r'Id="(rId\d+)"[^>]*Target="media/([^"]+)"', rels):
            rid_to_file[match.group(1)] = match.group(2)

        return rid_to_file

    def _parse_content(
        self,
        doc_xml: str,
        rid_to_num: Dict[str, int],
        styles: Optional[Dict[str, StyleInfo]] = None,
        font_size_hierarchy: Optional[Dict[int, int]] = None
    ) -> str:
        """Parse document.xml to extract text with image placeholders"""
        ns = self.NAMESPACES
        root = ET.fromstring(doc_xml)
        result = []

        styles = styles or {}
        font_size_hierarchy = font_size_hierarchy or {}

        for body in root.findall('.//w:body', ns):
            for elem in body:
                if elem.tag == f"{{{ns['w']}}}p":
                    para_text = self._parse_paragraph(
                        elem, rid_to_num, styles, font_size_hierarchy
                    )
                    if para_text:
                        result.append(para_text)

                elif elem.tag == f"{{{ns['w']}}}tbl":
                    table_text = self._parse_table(elem)
                    if table_text:
                        result.append(table_text)

        content = "\n\n".join(result)

        # Convert circled numbers to numbered list format if enabled
        if self.convert_circled_numbers:
            content = convert_circled_numbers(content)

        return content

    def _parse_content_blocks(
        self,
        doc_xml: str,
        rid_to_num: Dict[str, int],
        styles: Optional[Dict[str, StyleInfo]] = None,
        font_size_hierarchy: Optional[Dict[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """Parse document.xml to extract structured content blocks for JSON output"""
        ns = self.NAMESPACES
        root = ET.fromstring(doc_xml)
        blocks: List[Dict[str, Any]] = []

        styles = styles or {}
        font_size_hierarchy = font_size_hierarchy or {}

        for body in root.findall('.//w:body', ns):
            for elem in body:
                if elem.tag == f"{{{ns['w']}}}p":
                    block = self._parse_paragraph_block(
                        elem, rid_to_num, styles, font_size_hierarchy
                    )
                    if block:
                        blocks.append(block)

                elif elem.tag == f"{{{ns['w']}}}tbl":
                    block = self._parse_table_block(elem)
                    if block:
                        blocks.append(block)

        return blocks

    def _parse_paragraph_block(
        self,
        elem: ET.Element,
        rid_to_num: Dict[str, int],
        styles: Optional[Dict[str, StyleInfo]] = None,
        font_size_hierarchy: Optional[Dict[int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse a paragraph element to a content block"""
        ns = self.NAMESPACES
        para_parts = []
        image_indices = []

        styles = styles or {}
        font_size_hierarchy = font_size_hierarchy or {}

        for child in elem.iter():
            # Text
            if child.tag == f"{{{ns['w']}}}t" and child.text:
                para_parts.append(("text", child.text))

            # Image (blip in drawing)
            if child.tag == f"{{{ns['a']}}}blip":
                embed = child.get(f"{{{ns['r']}}}embed")
                if embed and embed in rid_to_num:
                    num = rid_to_num[embed]
                    image_indices.append(num)
                    para_parts.append(("image", num))

        # If paragraph only contains image(s), return image block(s)
        text_content = "".join(part[1] for part in para_parts if part[0] == "text")

        # Pure image paragraph
        if not text_content.strip() and image_indices:
            # Return first image as block (multiple images rare in single paragraph)
            return ImageBlock(index=image_indices[0]).to_dict()

        # Empty paragraph
        if not text_content.strip():
            return None

        # Check if it's a heading
        if self.hierarchy_mode != HierarchyMode.NONE:
            heading_level = self._get_heading_level(elem, styles, font_size_hierarchy)
            if heading_level:
                return HeadingBlock(content=text_content, level=heading_level).to_dict()

        # Regular paragraph (may contain inline images as placeholders)
        content = text_content
        if image_indices:
            # Include image placeholders in text
            content = "".join(
                part[1] if part[0] == "text" else self.image_placeholder.format(num=part[1])
                for part in para_parts
            )

        return ParagraphBlock(content=content).to_dict()

    def _parse_table_block(self, elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a table element to a content block"""
        table_data = self._parse_table_data(elem)
        if not table_data.rows:
            return None

        # Convert to simple rows format
        rows = []
        headers = None

        for row_idx, row in enumerate(table_data.rows):
            row_texts = []
            for cell in row:
                if not cell.is_merged_continuation:
                    row_texts.append(cell.text)
            if row_texts:
                rows.append(row_texts)

        # First row as headers if present
        if rows:
            headers = rows[0]
            rows = rows[1:] if len(rows) > 1 else []

        return TableBlock(
            rows=rows,
            headers=headers,
            metadata={
                "col_count": table_data.col_count,
                "row_count": table_data.row_count
            }
        ).to_dict()

    def _parse_paragraph(
        self,
        elem: ET.Element,
        rid_to_num: Dict[str, int],
        styles: Optional[Dict[str, StyleInfo]] = None,
        font_size_hierarchy: Optional[Dict[int, int]] = None
    ) -> str:
        """Parse a paragraph element with optional heading detection"""
        ns = self.NAMESPACES
        para_text = []

        styles = styles or {}
        font_size_hierarchy = font_size_hierarchy or {}

        for child in elem.iter():
            # Text
            if child.tag == f"{{{ns['w']}}}t" and child.text:
                para_text.append(child.text)

            # Image (blip in drawing)
            if child.tag == f"{{{ns['a']}}}blip":
                embed = child.get(f"{{{ns['r']}}}embed")
                if embed and embed in rid_to_num:
                    num = rid_to_num[embed]
                    placeholder = self.image_placeholder.format(num=num)
                    para_text.append(placeholder)

        text = "".join(para_text)

        # Apply heading markup if hierarchy detection is enabled
        if self.hierarchy_mode != HierarchyMode.NONE and text.strip():
            heading_level = None

            # Pattern-based detection uses text content
            if self.hierarchy_mode == HierarchyMode.PATTERN:
                heading_level = self._get_heading_level_by_pattern(text)
            else:
                # Style/font-size based detection uses XML element
                heading_level = self._get_heading_level(elem, styles, font_size_hierarchy)

            if heading_level:
                prefix = "#" * heading_level + " "
                return prefix + text

        return text

    @staticmethod
    def _escape_table_cell(text: str) -> str:
        """Escape special characters for markdown table cells.

        Handles:
        - Backslash (\\) -> (\\\\) - must be first to avoid double-escaping
        - Pipe (|) -> (\\|) - table cell delimiter
        - Asterisk (*) -> (\\*) - italic/bold marker
        - Underscore (_) -> (\\_) - italic/bold marker
        - Backtick (`) -> (\\`) - code marker
        - Newlines -> <br> - preserves multi-line content in table cells
        """
        if not text:
            return text
        # Order matters: escape backslash first, then other special chars
        text = text.replace('\\', '\\\\')
        text = text.replace('|', '\\|')
        text = text.replace('*', '\\*')
        text = text.replace('_', '\\_')
        text = text.replace('`', '\\`')
        # Replace newlines with <br> to preserve multi-line content
        text = text.replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')
        return text

    def _parse_table_data(self, elem: ET.Element) -> TableData:
        """Parse a table element to structured TableData with merge info preserved"""
        ns = self.NAMESPACES
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

        rows: List[List[TableCell]] = []
        vmerge_info: Dict[int, Dict[str, Any]] = {}  # col_idx -> {text, start_row, rowspan}

        row_idx = 0
        for row in elem.findall('.//w:tr', ns):
            row_cells: List[TableCell] = []
            col_idx = 0

            for cell in row.findall('.//w:tc', ns):
                # Extract text from each paragraph
                paragraphs = []
                for para in cell.findall('.//w:p', ns):
                    para_text = "".join(
                        t.text or ""
                        for t in para.findall('.//w:t', ns)
                    ).strip()
                    if para_text:
                        paragraphs.append(para_text)
                cell_text = "\n".join(paragraphs)

                # Get cell properties
                tcPr = cell.find('w:tcPr', ns)
                colspan = 1
                vmerge_type = None

                if tcPr is not None:
                    gs = tcPr.find('w:gridSpan', ns)
                    if gs is not None:
                        colspan = int(gs.get(w_ns + 'val', '1'))

                    vm = tcPr.find('w:vMerge', ns)
                    if vm is not None:
                        vmerge_type = vm.get(w_ns + 'val', 'continue')

                # Handle vertical merge tracking
                is_merged_continuation = False
                rowspan = 1

                if vmerge_type == 'restart':
                    # Start of vertical merge
                    vmerge_info[col_idx] = {
                        'text': cell_text,
                        'start_row': row_idx,
                        'rowspan': 1
                    }
                elif vmerge_type == 'continue':
                    # Continue vertical merge
                    is_merged_continuation = True
                    if col_idx in vmerge_info:
                        vmerge_info[col_idx]['rowspan'] += 1
                    cell_text = ''  # Merged cell has no text
                else:
                    # No vertical merge - finalize any previous merge
                    if col_idx in vmerge_info:
                        del vmerge_info[col_idx]

                # Create cell(s) based on colspan
                row_cells.append(TableCell(
                    text=cell_text,
                    colspan=colspan,
                    rowspan=rowspan,
                    is_header=(row_idx == 0),
                    is_merged_continuation=is_merged_continuation
                ))
                col_idx += colspan

            if row_cells:
                rows.append(row_cells)
                row_idx += 1

        # Update rowspan values for cells that start vertical merges
        for col_idx, info in vmerge_info.items():
            start_row = info['start_row']
            rowspan = info['rowspan']
            if start_row < len(rows):
                # Find the cell at that position
                current_col = 0
                for cell in rows[start_row]:
                    if current_col == col_idx:
                        cell.rowspan = rowspan
                        break
                    current_col += cell.colspan

        col_count = max((sum(c.colspan for c in row) for row in rows), default=0)

        return TableData(
            rows=rows,
            col_count=col_count,
            row_count=len(rows)
        )

    def _table_to_markdown(self, table_data: TableData) -> str:
        """Convert TableData to markdown format"""
        if not table_data.rows:
            return ""

        # Expand cells based on vertical/horizontal merge modes
        expanded_rows: List[List[str]] = []
        vmerge_values: Dict[int, str] = {}

        for row_idx, row in enumerate(table_data.rows):
            expanded_row: List[str] = []
            col_idx = 0

            for cell in row:
                text = cell.text.replace('\n', '<br>')

                # Handle vertical merge based on mode
                if cell.is_merged_continuation:
                    if self.vertical_merge == VerticalMergeMode.REPEAT:
                        text = vmerge_values.get(col_idx, '')
                    elif self.vertical_merge == VerticalMergeMode.EMPTY:
                        text = ''
                    elif self.vertical_merge == VerticalMergeMode.FIRST_ONLY:
                        text = ''
                elif cell.rowspan > 1:
                    vmerge_values[col_idx] = text

                # Handle horizontal merge based on mode
                if self.horizontal_merge == HorizontalMergeMode.EXPAND:
                    expanded_row.append(text)
                    for _ in range(cell.colspan - 1):
                        expanded_row.append('')
                elif self.horizontal_merge == HorizontalMergeMode.SINGLE:
                    expanded_row.append(text)
                elif self.horizontal_merge == HorizontalMergeMode.REPEAT:
                    for _ in range(cell.colspan):
                        expanded_row.append(text)

                col_idx += cell.colspan

            expanded_rows.append(expanded_row)

        if not expanded_rows:
            return ""

        # Normalize column count
        max_cols = max(len(row) for row in expanded_rows)
        for row in expanded_rows:
            while len(row) < max_cols:
                row.append('')

        # Convert to markdown
        md_rows = []
        for row in expanded_rows:
            escaped_cells = [self._escape_table_cell(cell) for cell in row]
            md_rows.append("| " + " | ".join(escaped_cells) + " |")

        header_sep = "| " + " | ".join(["---"] * max_cols) + " |"
        return md_rows[0] + "\n" + header_sep + "\n" + "\n".join(md_rows[1:])

    def _table_to_json(self, table_data: TableData) -> str:
        """Convert TableData to JSON format"""
        return json.dumps(table_data.to_dict(), ensure_ascii=False)

    def _table_to_html(self, table_data: TableData) -> str:
        """Convert TableData to HTML format with colspan/rowspan"""
        if not table_data.rows:
            return ""

        html_parts = ["<table>"]

        # Track cells to skip due to rowspan
        skip_cells: Dict[tuple, bool] = {}  # (row_idx, col_idx) -> True

        for row_idx, row in enumerate(table_data.rows):
            html_parts.append("  <tr>")
            col_idx = 0

            for cell in row:
                # Skip cells covered by rowspan
                while (row_idx, col_idx) in skip_cells:
                    col_idx += 1

                if cell.is_merged_continuation:
                    col_idx += cell.colspan
                    continue

                tag = "th" if cell.is_header else "td"
                attrs = []

                if cell.colspan > 1:
                    attrs.append(f'colspan="{cell.colspan}"')
                if cell.rowspan > 1:
                    attrs.append(f'rowspan="{cell.rowspan}"')
                    # Mark cells to skip in subsequent rows
                    for r in range(row_idx + 1, row_idx + cell.rowspan):
                        for c in range(col_idx, col_idx + cell.colspan):
                            skip_cells[(r, c)] = True

                attr_str = " " + " ".join(attrs) if attrs else ""
                text = cell.text.replace('\n', '<br>')
                html_parts.append(f"    <{tag}{attr_str}>{text}</{tag}>")

                col_idx += cell.colspan

            html_parts.append("  </tr>")

        html_parts.append("</table>")
        return "\n".join(html_parts)

    def _table_to_text(self, table_data: TableData) -> str:
        """Convert TableData to tab-separated text"""
        if not table_data.rows:
            return ""

        lines = []
        for row in table_data.rows:
            cells = []
            for cell in row:
                if not cell.is_merged_continuation:
                    text = cell.text.replace('\n', ' ').replace('\t', ' ')
                    cells.append(text)
            lines.append("\t".join(cells))

        return "\n".join(lines)

    def _parse_table(self, elem: ET.Element) -> str:
        """Parse a table element to the configured format"""
        table_data = self._parse_table_data(elem)

        if self.table_format == TableFormat.JSON:
            return self._table_to_json(table_data)
        elif self.table_format == TableFormat.HTML:
            return self._table_to_html(table_data)
        elif self.table_format == TableFormat.TEXT:
            return self._table_to_text(table_data)
        else:  # MARKDOWN (default)
            return self._table_to_markdown(table_data)


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
    convert_circled_numbers: bool = True,
    heading_patterns: Optional[List[Tuple[str, int]]] = None,
) -> Union[ParseResult, List[ParseResult]]:
    """
    Convenience function to parse DOCX file(s).

    Args:
        docx_path: Path to DOCX file, or list of paths for batch processing
        output_dir: Directory to save images
        extract_images: Whether to extract images
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
            - "pattern": Use custom text patterns (requires heading_patterns)
        max_heading_level: Maximum heading depth (1-6, default: 6)
        table_format: Output format for tables
            - "markdown": Markdown table format (default)
            - "json": Structured JSON with merge info preserved
            - "html": HTML table with colspan/rowspan
            - "text": Tab-separated plain text
        vision_provider: VisionProvider instance for image description (optional)
        auto_describe_images: Automatically generate image descriptions (default: False)
        image_prompts: Dictionary mapping image index to custom prompt (optional)
            - Apply different prompts per image for optimized analysis
            - Example: {1: "Analyze this blueprint...", 2: "Describe this chart..."}
        save_file: Whether to save content file when output_dir is specified (default: False)
            - False: Don't save content file (only images saved)
            - True: Save content file based on output_format
            - Example: output_format="markdown", save_file=True saves "output/document.md"
        convert_images: Convert non-standard image formats to PNG (default: True)
            - WDP (Windows Media Photo) -> PNG
            - TMP (detect actual format from magic bytes) -> PNG/JPEG
            - EMF/WMF (Windows Metafile) -> PNG (requires PIL)
        convert_circled_numbers: Convert circled numbers to numbered list (default: True)
            - ① ② ③ -> 1. 2. 3.
            - Content between numbers is indented
        heading_patterns: Custom patterns for hierarchy_mode="pattern"
            List of (pattern, heading_level) tuples.
            - Literal: ("I. ", 1), ("1. ", 2), ("1)", 3), ("(1)", 4)
            - Regex: ("^[IVX]+\\. ", 1), ("^\\d+\\. ", 2)
            Example: [("I. ", 1), ("1. ", 2), ("1)", 3), ("(1)", 4)]

    Returns:
        ParseResult (single file) or List[ParseResult] (multiple files)

    Example:
        # Multiple documents at once
        results = parse_docx([
            "doc1.docx",
            "doc2.docx",
            "doc3.docx"
        ], output_dir="output")
        for result in results:
            print(result.metadata.core.title)

        # Default: markdown with metadata
        result = parse_docx("document.docx", "output")
        print(result.metadata.core.creator)  # Author
        print(result.metadata.app.pages)     # Page count

        # Plain text output
        result = parse_docx("document.docx", output_format="text")

        # With heading detection
        result = parse_docx("document.docx", hierarchy_mode="font_size")
        # Output: "# Title\\n\\n## Section\\n\\n..."

        # With JSON table format (preserves merge info)
        result = parse_docx("document.docx", table_format="json")
        # Tables output as: {"type": "table", "rows": [...], ...}

        # With HTML table format
        result = parse_docx("document.docx", table_format="html")
        # Tables output as: <table><tr><td colspan="2">...</td></tr>...</table>

        # With vision provider for automatic image description
        from docx_parser.vision import create_vision_provider
        provider = create_vision_provider("openai")
        result = parse_docx("document.docx", "output",
                          vision_provider=provider,
                          auto_describe_images=True)
        # Output: [IMAGE_1] -> [Image: 회사 로고 이미지...]

        # With custom prompts per image (image_prompts)
        result = parse_docx("document.docx", "output",
                          vision_provider=provider,
                          auto_describe_images=True,
                          image_prompts={
                              1: "이 기술 도면을 상세히 분석해주세요...",
                              2: "이 차트의 트렌드를 설명해주세요...",
                          })

        # Get LangChain-compatible metadata
        metadata = result.to_langchain_metadata()

        # Auto-save content to output_dir (uses output_format)
        result = parse_docx("document.docx", output_dir="output",
                          output_format="markdown", save_file=True)
        # Saves: output/document.md, output/images/document/

        # Save as JSON
        result = parse_docx("document.docx", output_dir="output",
                          output_format="json", save_file=True)
        # Saves: output/document.json
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
        convert_circled_numbers=convert_circled_numbers,
        heading_patterns=heading_patterns,
    )

    def _save_result(result: ParseResult, out_dir: Path, fmt: OutputFormat) -> None:
        """Save result based on output_format"""
        if not out_dir:
            return

        # Get base filename from source (without extension)
        base_name = result.source.stem if result.source else "output"

        if fmt == OutputFormat.MARKDOWN:
            result.save_markdown(out_dir / f"{base_name}.md")
        elif fmt == OutputFormat.TEXT:
            result.save_text(out_dir / f"{base_name}.txt")
        elif fmt == OutputFormat.JSON:
            result.save_json(out_dir / f"{base_name}.json")

    # Handle list of paths
    if isinstance(docx_path, list):
        results = []
        for path in docx_path:
            result = parser.parse(path, output_dir)
            # Auto-generate image descriptions if requested
            if auto_describe_images and vision_provider and result.images_list:
                result.describe_images(vision_provider, image_prompts=image_prompts)
                result.content = result.replace_placeholders(result.image_descriptions)
            # Auto-save if save_file is True
            if output_dir and save_file:
                _save_result(result, Path(output_dir), OutputFormat(output_format))
            results.append(result)
        return results

    # Single path
    result = parser.parse(docx_path, output_dir)

    # Auto-generate image descriptions if requested
    if auto_describe_images and vision_provider and result.images_list:
        result.describe_images(vision_provider, image_prompts=image_prompts)
        result.content = result.replace_placeholders(result.image_descriptions)

    # Auto-save if save_file is True
    if output_dir and save_file:
        _save_result(result, Path(output_dir), OutputFormat(output_format))

    return result
