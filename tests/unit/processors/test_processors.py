"""
Unit tests for DOCX processors.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

from docx_parser.models import (
    AppMetadata,
    CoreMetadata,
    DocxMetadata,
    HierarchyMode,
    HorizontalMergeMode,
    OutputFormat,
    StyleInfo,
    TableFormat,
    VerticalMergeMode,
)
from docx_parser.processors import (
    ContentProcessor,
    HeadingDetector,
    ImageProcessor,
    MetadataProcessor,
    ParsingContext,
    Processor,
    StyleProcessor,
    TableProcessor,
    escape_table_cell,
    extract_metadata,
)
from docx_parser.utils.xml import NAMESPACES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def namespaces() -> Dict[str, str]:
    """Standard OOXML namespaces."""
    return NAMESPACES


@pytest.fixture
def sample_core_xml() -> str:
    """Sample core.xml content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/">
    <dc:title>Test Document</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:subject>Test Subject</dc:subject>
    <cp:keywords>test, keywords</cp:keywords>
    <cp:revision>5</cp:revision>
    <dcterms:created>2024-01-15T10:30:00Z</dcterms:created>
    <dcterms:modified>2024-01-20T15:45:00Z</dcterms:modified>
</cp:coreProperties>"""


@pytest.fixture
def sample_app_xml() -> str:
    """Sample app.xml content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
    <Template>Normal.dotm</Template>
    <TotalTime>120</TotalTime>
    <Pages>10</Pages>
    <Words>5000</Words>
    <Characters>30000</Characters>
    <Application>Microsoft Word</Application>
    <AppVersion>16.0</AppVersion>
</Properties>"""


@pytest.fixture
def sample_styles_xml() -> str:
    """Sample styles.xml content."""
    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="{w_ns}">
    <w:style w:type="paragraph" w:styleId="Heading1">
        <w:name w:val="Heading 1"/>
        <w:pPr>
            <w:outlineLvl w:val="0"/>
        </w:pPr>
        <w:rPr>
            <w:sz w:val="44"/>
        </w:rPr>
    </w:style>
    <w:style w:type="paragraph" w:styleId="Heading2">
        <w:name w:val="Heading 2"/>
        <w:pPr>
            <w:outlineLvl w:val="1"/>
        </w:pPr>
        <w:rPr>
            <w:sz w:val="36"/>
        </w:rPr>
    </w:style>
    <w:style w:type="paragraph" w:styleId="Normal">
        <w:name w:val="Normal"/>
        <w:rPr>
            <w:sz w:val="24"/>
        </w:rPr>
    </w:style>
</w:styles>"""


@pytest.fixture
def sample_document_xml() -> str:
    """Sample document.xml content."""
    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p>
            <w:pPr>
                <w:pStyle w:val="Heading1"/>
            </w:pPr>
            <w:r>
                <w:t>Title</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>This is a paragraph.</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>"""


@pytest.fixture
def sample_rels_xml() -> str:
    """Sample document.xml.rels content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Target="media/image1.png" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"/>
    <Relationship Id="rId2" Target="media/image2.jpg" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"/>
</Relationships>"""


@pytest.fixture
def sample_table_xml() -> ET.Element:
    """Sample table XML element."""
    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc><w:p><w:r><w:t>Header 1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Header 2</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc><w:p><w:r><w:t>Cell 1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Cell 2</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc><w:p><w:r><w:t>Cell 3</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Cell 4</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
    return ET.fromstring(table_xml)


@pytest.fixture
def mock_docx_zip(sample_core_xml, sample_app_xml, sample_styles_xml, sample_document_xml, sample_rels_xml):
    """Create a mock DOCX zip file in memory."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("docProps/core.xml", sample_core_xml)
        z.writestr("docProps/app.xml", sample_app_xml)
        z.writestr("word/styles.xml", sample_styles_xml)
        z.writestr("word/document.xml", sample_document_xml)
        z.writestr("word/_rels/document.xml.rels", sample_rels_xml)
        # Add fake image
        z.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        z.writestr("word/media/image2.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    buffer.seek(0)
    return zipfile.ZipFile(buffer, "r")


# ============================================================================
# ParsingContext Tests
# ============================================================================


class TestParsingContext:
    """Tests for ParsingContext dataclass."""

    def test_default_creation(self):
        """Test default context creation."""
        context = ParsingContext()
        assert context.zip_file is None
        assert context.styles == {}
        assert context.font_size_hierarchy == {}
        assert context.images == []
        assert context.rid_to_file == {}
        assert context.rid_to_num == {}

    def test_with_zip_file(self, mock_docx_zip):
        """Test context with zip file."""
        context = ParsingContext(zip_file=mock_docx_zip)
        assert context.zip_file is not None

    def test_mutable_fields_are_independent(self):
        """Test that mutable fields are independent between instances."""
        ctx1 = ParsingContext()
        ctx2 = ParsingContext()
        ctx1.styles["test"] = StyleInfo(style_id="test")
        assert "test" not in ctx2.styles


# ============================================================================
# MetadataProcessor Tests
# ============================================================================


class TestMetadataProcessor:
    """Tests for MetadataProcessor."""

    def test_process_extracts_core_metadata(self, mock_docx_zip):
        """Test extraction of core metadata."""
        processor = MetadataProcessor()
        context = ParsingContext(zip_file=mock_docx_zip)
        result = processor.process(context)

        assert result.core.title == "Test Document"
        assert result.core.creator == "Test Author"
        assert result.core.subject == "Test Subject"
        assert result.core.keywords == "test, keywords"
        assert result.core.revision == 5

    def test_process_extracts_app_metadata(self, mock_docx_zip):
        """Test extraction of app metadata."""
        processor = MetadataProcessor()
        context = ParsingContext(zip_file=mock_docx_zip)
        result = processor.process(context)

        assert result.app.template == "Normal.dotm"
        assert result.app.total_time == 120
        assert result.app.pages == 10
        assert result.app.words == 5000
        assert result.app.application == "Microsoft Word"

    def test_process_with_docx_path(self, mock_docx_zip, tmp_path):
        """Test extraction with file path info."""
        processor = MetadataProcessor()
        context = ParsingContext(zip_file=mock_docx_zip)
        test_path = tmp_path / "test.docx"
        test_path.write_bytes(b"test content")

        result = processor.process(context, docx_path=test_path)
        assert result.file_name == "test.docx"
        assert result.file_size > 0

    def test_process_without_zip_returns_empty(self):
        """Test empty context returns empty metadata."""
        processor = MetadataProcessor()
        context = ParsingContext()
        result = processor.process(context)

        assert result.core.title is None
        assert result.app.pages is None

    def test_missing_core_xml_returns_empty_core(self):
        """Test missing core.xml returns empty CoreMetadata."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("word/document.xml", "<document/>")
        buffer.seek(0)

        processor = MetadataProcessor()
        with zipfile.ZipFile(buffer, "r") as z:
            context = ParsingContext(zip_file=z)
            result = processor.process(context)

        assert result.core.title is None


class TestExtractMetadataFunction:
    """Tests for extract_metadata convenience function."""

    def test_extract_metadata(self, mock_docx_zip):
        """Test the convenience function."""
        result = extract_metadata(mock_docx_zip)
        assert result.core.title == "Test Document"


# ============================================================================
# StyleProcessor Tests
# ============================================================================


class TestStyleProcessor:
    """Tests for StyleProcessor."""

    def test_load_styles(self, mock_docx_zip):
        """Test loading styles from DOCX."""
        processor = StyleProcessor()
        styles = processor.load_styles(mock_docx_zip)

        assert "Heading1" in styles
        assert "Heading2" in styles
        assert "Normal" in styles
        assert styles["Heading1"].outline_level == 0
        assert styles["Heading2"].outline_level == 1

    def test_load_styles_font_size(self, mock_docx_zip):
        """Test font size extraction from styles."""
        processor = StyleProcessor()
        styles = processor.load_styles(mock_docx_zip)

        assert styles["Heading1"].font_size == 44
        assert styles["Heading2"].font_size == 36
        assert styles["Normal"].font_size == 24

    def test_load_styles_missing_file(self):
        """Test loading from DOCX without styles.xml."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("word/document.xml", "<document/>")
        buffer.seek(0)

        processor = StyleProcessor()
        with zipfile.ZipFile(buffer, "r") as z:
            styles = processor.load_styles(z)

        assert styles == {}

    def test_process_method(self, mock_docx_zip):
        """Test process method returns styles."""
        processor = StyleProcessor()
        context = ParsingContext(zip_file=mock_docx_zip)
        styles = processor.process(context)

        assert "Heading1" in styles

    def test_get_paragraph_font_size(self, mock_docx_zip, namespaces):
        """Test font size detection from paragraph."""
        processor = StyleProcessor()
        w_ns = namespaces["w"]

        # Create paragraph with font size
        p = ET.Element(f"{{{w_ns}}}p")
        r = ET.SubElement(p, f"{{{w_ns}}}r")
        rPr = ET.SubElement(r, f"{{{w_ns}}}rPr")
        sz = ET.SubElement(rPr, f"{{{w_ns}}}sz")
        sz.set(f"{{{w_ns}}}val", "28")

        size = processor.get_paragraph_font_size(p, {})
        assert size == 28

    def test_collect_font_sizes(self, sample_document_xml, mock_docx_zip):
        """Test font size collection from document."""
        processor = StyleProcessor()
        styles = processor.load_styles(mock_docx_zip)

        # Modify document to have explicit font sizes
        sizes = processor.collect_font_sizes(sample_document_xml, styles)
        # May be empty or contain sizes from styles
        assert isinstance(sizes, set)

    def test_build_hierarchy(self, sample_document_xml, mock_docx_zip):
        """Test building font size hierarchy."""
        processor = StyleProcessor()
        styles = processor.load_styles(mock_docx_zip)

        hierarchy = processor.build_hierarchy(sample_document_xml, styles)
        assert isinstance(hierarchy, dict)


# ============================================================================
# HeadingDetector Tests
# ============================================================================


class TestHeadingDetector:
    """Tests for HeadingDetector."""

    def test_detect_none_mode(self, namespaces):
        """Test NONE mode always returns None."""
        detector = HeadingDetector(HierarchyMode.NONE)
        w_ns = namespaces["w"]

        p = ET.Element(f"{{{w_ns}}}p")
        result = detector.detect(p, {}, {})
        assert result is None

    def test_detect_style_mode(self, namespaces):
        """Test STYLE mode detection."""
        detector = HeadingDetector(HierarchyMode.STYLE)
        w_ns = namespaces["w"]

        # Create paragraph with Heading1 style
        p = ET.Element(f"{{{w_ns}}}p")
        pPr = ET.SubElement(p, f"{{{w_ns}}}pPr")
        pStyle = ET.SubElement(pPr, f"{{{w_ns}}}pStyle")
        pStyle.set(f"{{{w_ns}}}val", "Heading1")

        styles = {
            "Heading1": StyleInfo(style_id="Heading1", outline_level=0),
        }

        result = detector.detect(p, styles, {})
        assert result == 1

    def test_detect_pattern_mode(self, namespaces):
        """Test PATTERN mode detection."""
        import re
        patterns = [(re.compile(r"^Chapter \d+"), 1)]
        detector = HeadingDetector(
            HierarchyMode.PATTERN,
            heading_patterns=patterns,
        )

        result = detector._detect_by_pattern("Chapter 1: Introduction")
        assert result == 1

    def test_detect_pattern_no_match(self, namespaces):
        """Test PATTERN mode with no match."""
        import re
        patterns = [(re.compile(r"^Chapter \d+"), 1)]
        detector = HeadingDetector(
            HierarchyMode.PATTERN,
            heading_patterns=patterns,
        )

        result = detector._detect_by_pattern("Regular paragraph")
        assert result is None


# ============================================================================
# TableProcessor Tests
# ============================================================================


class TestTableProcessor:
    """Tests for TableProcessor."""

    def test_parse_simple_table(self, namespaces):
        """Test parsing a simple table."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # Create simple 2x2 table
        tbl = ET.Element(f"{{{w_ns}}}tbl")
        for row_idx in range(2):
            tr = ET.SubElement(tbl, f"{{{w_ns}}}tr")
            for col_idx in range(2):
                tc = ET.SubElement(tr, f"{{{w_ns}}}tc")
                p = ET.SubElement(tc, f"{{{w_ns}}}p")
                r = ET.SubElement(p, f"{{{w_ns}}}r")
                t = ET.SubElement(r, f"{{{w_ns}}}t")
                t.text = f"Cell {row_idx},{col_idx}"

        table_data = processor.parse_table_data(tbl)
        assert table_data.row_count == 2
        assert table_data.col_count == 2

    def test_parse_table_to_markdown(self, namespaces):
        """Test converting table to markdown."""
        processor = TableProcessor(table_format=TableFormat.MARKDOWN)
        w_ns = namespaces["w"]

        tbl = ET.Element(f"{{{w_ns}}}tbl")
        for row_idx in range(2):
            tr = ET.SubElement(tbl, f"{{{w_ns}}}tr")
            for col_idx in range(2):
                tc = ET.SubElement(tr, f"{{{w_ns}}}tc")
                p = ET.SubElement(tc, f"{{{w_ns}}}p")
                r = ET.SubElement(p, f"{{{w_ns}}}r")
                t = ET.SubElement(r, f"{{{w_ns}}}t")
                t.text = f"Cell{row_idx}{col_idx}"

        result = processor.parse_table(tbl)
        assert "|" in result
        assert "Cell00" in result

    def test_parse_table_block(self, namespaces):
        """Test parsing table as block."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        tbl = ET.Element(f"{{{w_ns}}}tbl")
        tr = ET.SubElement(tbl, f"{{{w_ns}}}tr")
        tc = ET.SubElement(tr, f"{{{w_ns}}}tc")
        p = ET.SubElement(tc, f"{{{w_ns}}}p")
        r = ET.SubElement(p, f"{{{w_ns}}}r")
        t = ET.SubElement(r, f"{{{w_ns}}}t")
        t.text = "Header"

        block = processor.parse_table_block(tbl)
        assert block is not None
        assert block["type"] == "table"


class TestEscapeTableCell:
    """Tests for escape_table_cell function."""

    def test_escapes_pipe(self):
        """Test pipe character escaping."""
        assert escape_table_cell("a|b") == "a\\|b"

    def test_escapes_backslash(self):
        """Test backslash escaping."""
        assert escape_table_cell("a\\b") == "a\\\\b"

    def test_escapes_asterisk(self):
        """Test asterisk escaping."""
        assert escape_table_cell("a*b") == "a\\*b"

    def test_escapes_underscore(self):
        """Test underscore escaping."""
        assert escape_table_cell("a_b") == "a\\_b"

    def test_converts_newlines(self):
        """Test newline conversion."""
        assert escape_table_cell("a\nb") == "a<br>b"

    def test_empty_string(self):
        """Test empty string handling."""
        assert escape_table_cell("") == ""


# ============================================================================
# ImageProcessor Tests
# ============================================================================


class TestImageProcessor:
    """Tests for ImageProcessor."""

    def test_parse_relationships(self, mock_docx_zip):
        """Test parsing image relationships."""
        processor = ImageProcessor()
        rid_to_file = processor.parse_relationships(mock_docx_zip)

        assert "rId1" in rid_to_file
        assert rid_to_file["rId1"] == "image1.png"
        assert "rId2" in rid_to_file
        assert rid_to_file["rId2"] == "image2.jpg"

    def test_parse_relationships_missing_rels(self):
        """Test handling missing rels file."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("word/document.xml", "<document/>")
        buffer.seek(0)

        processor = ImageProcessor()
        with zipfile.ZipFile(buffer, "r") as z:
            rid_to_file = processor.parse_relationships(z)

        assert rid_to_file == {}

    def test_process_extracts_images(self, mock_docx_zip, tmp_path):
        """Test image extraction."""
        processor = ImageProcessor(extract_images=True, convert_images=False)
        context = ParsingContext(zip_file=mock_docx_zip)

        images, mapping, images_list = processor.process(
            context, output_dir=tmp_path, docx_stem="test"
        )

        assert len(images_list) == 2
        assert 1 in mapping
        assert 2 in mapping

    def test_process_without_extraction(self, mock_docx_zip):
        """Test processing without image extraction."""
        processor = ImageProcessor(extract_images=False)
        context = ParsingContext(zip_file=mock_docx_zip)

        images, mapping, images_list = processor.process(context)

        assert len(images_list) == 2
        assert images_list[0].data is None  # No data when not extracting

    def test_get_placeholder(self):
        """Test placeholder generation."""
        processor = ImageProcessor(image_placeholder="[IMG_{num}]")
        assert processor.get_placeholder(1) == "[IMG_1]"
        assert processor.get_placeholder(42) == "[IMG_42]"


# ============================================================================
# ContentProcessor Tests
# ============================================================================


class TestContentProcessor:
    """Tests for ContentProcessor."""

    def test_parse_content_basic(self, sample_document_xml, namespaces):
        """Test basic content parsing."""
        processor = ContentProcessor()
        result = processor.parse_content(sample_document_xml, {}, {}, {})

        assert "Title" in result
        assert "This is a paragraph" in result

    def test_parse_content_with_heading(self, sample_document_xml, namespaces):
        """Test content parsing with heading detection."""
        styles = {
            "Heading1": StyleInfo(style_id="Heading1", outline_level=0),
        }
        processor = ContentProcessor(hierarchy_mode=HierarchyMode.STYLE)
        result = processor.parse_content(sample_document_xml, {}, styles, {})

        assert "# Title" in result

    def test_parse_content_blocks(self, sample_document_xml, namespaces):
        """Test parsing to content blocks."""
        styles = {
            "Heading1": StyleInfo(style_id="Heading1", outline_level=0),
        }
        processor = ContentProcessor(hierarchy_mode=HierarchyMode.STYLE)
        blocks = processor.parse_content_blocks(sample_document_xml, {}, styles, {})

        assert len(blocks) > 0
        assert any(b.get("type") == "heading" for b in blocks)

    def test_to_text_conversion(self):
        """Test markdown to text conversion."""
        markdown = "| Header |\n| --- |\n| Cell |"
        text = ContentProcessor.to_text(markdown)

        assert "|" not in text
        assert "Header" in text


# ============================================================================
# Processor Protocol Tests
# ============================================================================


class TestProcessorProtocol:
    """Tests for Processor protocol compliance."""

    def test_metadata_processor_is_processor(self):
        """Test MetadataProcessor implements protocol."""
        assert isinstance(MetadataProcessor(), Processor)

    def test_style_processor_is_processor(self):
        """Test StyleProcessor implements protocol."""
        assert isinstance(StyleProcessor(), Processor)

    def test_table_processor_is_processor(self):
        """Test TableProcessor implements protocol."""
        assert isinstance(TableProcessor(), Processor)

    def test_image_processor_is_processor(self):
        """Test ImageProcessor implements protocol."""
        assert isinstance(ImageProcessor(), Processor)

    def test_content_processor_is_processor(self):
        """Test ContentProcessor implements protocol."""
        assert isinstance(ContentProcessor(), Processor)


# ============================================================================
# Extended Coverage Tests
# ============================================================================


class TestTableProcessorExtended:
    """Extended tests for TableProcessor coverage."""

    def test_table_format_text(self, sample_table_xml):
        """Test table conversion to text format."""
        processor = TableProcessor(table_format=TableFormat.TEXT)
        result = processor.parse_table(sample_table_xml)

        assert result
        # Text format uses tabs
        assert "\t" in result

    def test_table_format_html(self, sample_table_xml):
        """Test table conversion to HTML format."""
        processor = TableProcessor(table_format=TableFormat.HTML)
        result = processor.parse_table(sample_table_xml)

        assert result
        assert "<table>" in result
        assert "<tr>" in result
        assert "</table>" in result

    def test_table_format_json(self, sample_table_xml):
        """Test table conversion to JSON format."""
        processor = TableProcessor(table_format=TableFormat.JSON)
        result = processor.parse_table(sample_table_xml)

        assert result
        # Should be valid JSON structure
        import json
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "rows" in parsed

    def test_vertical_merge_empty_mode(self, sample_table_xml):
        """Test vertical merge with EMPTY mode."""
        processor = TableProcessor(
            vertical_merge=VerticalMergeMode.EMPTY,
            table_format=TableFormat.MARKDOWN
        )
        result = processor.parse_table(sample_table_xml)

        assert result

    def test_vertical_merge_first_only_mode(self, sample_table_xml):
        """Test vertical merge with FIRST_ONLY mode."""
        processor = TableProcessor(
            vertical_merge=VerticalMergeMode.FIRST_ONLY,
            table_format=TableFormat.MARKDOWN
        )
        result = processor.parse_table(sample_table_xml)

        assert result

    def test_horizontal_merge_single_mode(self, sample_table_xml):
        """Test horizontal merge with SINGLE mode."""
        processor = TableProcessor(
            horizontal_merge=HorizontalMergeMode.SINGLE,
            table_format=TableFormat.MARKDOWN
        )
        result = processor.parse_table(sample_table_xml)

        assert result

    def test_horizontal_merge_repeat_mode(self, sample_table_xml):
        """Test horizontal merge with REPEAT mode."""
        processor = TableProcessor(
            horizontal_merge=HorizontalMergeMode.REPEAT,
            table_format=TableFormat.MARKDOWN
        )
        result = processor.parse_table(sample_table_xml)

        assert result


class TestContentProcessorExtended:
    """Extended tests for ContentProcessor coverage."""

    def test_content_processor_font_size_mode(self, sample_document_xml):
        """Test content processor with font size hierarchy mode."""
        processor = ContentProcessor(hierarchy_mode=HierarchyMode.FONT_SIZE)
        styles = {}
        font_hierarchy = {32: 1, 24: 2}  # 32pt -> H1, 24pt -> H2
        blocks = processor.parse_content_blocks(sample_document_xml, {}, styles, font_hierarchy)

        assert isinstance(blocks, list)

    def test_content_processor_auto_mode(self, sample_document_xml):
        """Test content processor with auto hierarchy mode."""
        styles = {
            "Heading1": StyleInfo(style_id="Heading1", outline_level=0),
        }
        processor = ContentProcessor(hierarchy_mode=HierarchyMode.AUTO)
        blocks = processor.parse_content_blocks(sample_document_xml, {}, styles, {})

        assert isinstance(blocks, list)

    def test_content_processor_none_mode(self, sample_document_xml):
        """Test content processor with no hierarchy detection."""
        processor = ContentProcessor(hierarchy_mode=HierarchyMode.NONE)
        blocks = processor.parse_content_blocks(sample_document_xml, {}, {}, {})

        assert isinstance(blocks, list)
        # No headings should be detected
        assert all(b.get("type") != "heading" for b in blocks)

    def test_content_processor_with_table_processor(self, sample_document_xml):
        """Test content processor with table processor integration."""
        table_proc = TableProcessor()
        processor = ContentProcessor(
            hierarchy_mode=HierarchyMode.STYLE,
            table_processor=table_proc
        )

        # Parse content - this tests the table integration path
        content = processor.parse_content(sample_document_xml, {}, {}, {})
        assert isinstance(content, str)

    def test_content_processor_process_method(self, mock_docx_zip, sample_document_xml):
        """Test content processor process method."""
        processor = ContentProcessor()

        context = ParsingContext(
            zip_file=mock_docx_zip,
            doc_xml=sample_document_xml,
            rid_to_num={},
            styles={},
            font_size_hierarchy={}
        )

        result = processor.process(context)
        assert isinstance(result, str)

    def test_content_processor_process_with_none_xml(self, mock_docx_zip):
        """Test content processor process method with None XML."""
        processor = ContentProcessor()

        context = ParsingContext(
            zip_file=mock_docx_zip,
            doc_xml=None,  # None XML
        )

        result = processor.process(context)
        assert result == ""

    def test_content_processor_to_text(self):
        """Test ContentProcessor.to_text static method."""
        markdown = "# Heading\n\n| Col1 | Col2 |\n| --- | --- |\n| A | B |"
        text = ContentProcessor.to_text(markdown)

        # Should remove markdown table syntax
        assert "| --- |" not in text
        assert "Heading" in text


class TestStyleProcessorExtended:
    """Extended tests for StyleProcessor coverage."""

    def test_style_processor_initialization(self):
        """Test style processor initialization."""
        processor = StyleProcessor()
        assert processor._namespaces is not None

    def test_style_processor_with_custom_namespaces(self, namespaces):
        """Test style processor with custom namespaces."""
        processor = StyleProcessor(namespaces=namespaces)
        assert processor._namespaces == namespaces


class TestMetadataProcessorExtended:
    """Extended tests for MetadataProcessor coverage."""

    def test_metadata_processor_initialization(self):
        """Test metadata processor initialization."""
        processor = MetadataProcessor()
        assert processor is not None


class TestImageProcessorExtended:
    """Extended tests for ImageProcessor coverage."""

    def test_image_processor_custom_placeholder(self):
        """Test image processor with custom placeholder."""
        processor = ImageProcessor(image_placeholder="<<IMG_{num}>>")
        assert processor._image_placeholder == "<<IMG_{num}>>"

    def test_image_processor_extract_disabled(self):
        """Test image processor with extraction disabled."""
        processor = ImageProcessor(extract_images=False)
        assert processor._extract_images is False

    def test_image_processor_convert_disabled(self):
        """Test image processor with conversion disabled."""
        processor = ImageProcessor(convert_images=False)
        assert processor._convert_images is False


class TestHeadingDetectorExtended:
    """Extended tests for HeadingDetector coverage."""

    def test_heading_detector_none_mode(self):
        """Test heading detector with NONE mode."""
        detector = HeadingDetector(hierarchy_mode=HierarchyMode.NONE)
        assert detector is not None

    def test_heading_detector_style_mode(self):
        """Test heading detector with STYLE mode."""
        detector = HeadingDetector(hierarchy_mode=HierarchyMode.STYLE, max_heading_level=4)
        assert detector._max_heading_level == 4

    def test_heading_detector_font_size_mode(self):
        """Test heading detector with FONT_SIZE mode."""
        detector = HeadingDetector(hierarchy_mode=HierarchyMode.FONT_SIZE)
        assert detector is not None

    def test_heading_detector_auto_mode(self):
        """Test heading detector with AUTO mode."""
        detector = HeadingDetector(hierarchy_mode=HierarchyMode.AUTO)
        assert detector is not None


class TestEscapeTableCell:
    """Tests for escape_table_cell function."""

    def test_escape_pipe_character(self):
        """Test escaping pipe character."""
        result = escape_table_cell("Hello | World")
        assert "\\|" in result

    def test_escape_newline_character(self):
        """Test escaping newline character."""
        result = escape_table_cell("Line1\nLine2")
        assert "<br>" in result

    def test_escape_empty_string(self):
        """Test escaping empty string."""
        result = escape_table_cell("")
        assert result == ""

    def test_escape_normal_text(self):
        """Test escaping normal text."""
        result = escape_table_cell("Hello World")
        assert result == "Hello World"


# ============================================================================
# Extended Coverage Tests for TableProcessor (67% → 90%)
# ============================================================================


class TestTableProcessorCoverage:
    """Tests to improve TableProcessor coverage from 67% to 90%."""

    def test_process_with_none_element(self):
        """Test process() returns empty string when element is None."""
        processor = TableProcessor()
        context = ParsingContext()
        result = processor.process(context, element=None)
        assert result == ""

    def test_process_without_element_kwarg(self):
        """Test process() returns empty string when element kwarg missing."""
        processor = TableProcessor()
        context = ParsingContext()
        result = processor.process(context)
        assert result == ""

    def test_parse_table_with_gridspan(self, namespaces):
        """Test table with horizontal merge (gridSpan)."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # Create table with gridSpan (horizontal merge)
        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:gridSpan w:val="2"/>
            </w:tcPr>
            <w:p><w:r><w:t>Merged Header</w:t></w:r></w:p>
        </w:tc>
    </w:tr>
    <w:tr>
        <w:tc><w:p><w:r><w:t>Cell 1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Cell 2</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        assert table_data.row_count == 2
        # First row has 1 cell with colspan=2
        assert table_data.rows[0][0].colspan == 2
        assert table_data.rows[0][0].text == "Merged Header"

    def test_parse_table_with_vmerge_restart(self, namespaces):
        """Test table with vertical merge (vMerge restart)."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # Create table with vMerge
        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:vMerge w:val="restart"/>
            </w:tcPr>
            <w:p><w:r><w:t>Merged Start</w:t></w:r></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>Header 2</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:vMerge/>
            </w:tcPr>
            <w:p><w:r><w:t></w:t></w:r></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>Cell 2</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        assert table_data.row_count == 2
        # First cell should have rowspan > 1
        assert table_data.rows[0][0].rowspan == 2
        # Second row's first cell is continuation
        assert table_data.rows[1][0].is_merged_continuation is True

    def test_parse_table_with_vmerge_continue(self, namespaces):
        """Test table with vMerge continue (no val attribute defaults to continue)."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # Create 3-row table with vMerge spanning all rows
        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge w:val="restart"/></w:tcPr>
            <w:p><w:r><w:t>Start</w:t></w:r></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge/></w:tcPr>
            <w:p></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>B</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge/></w:tcPr>
            <w:p></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>C</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        assert table_data.row_count == 3
        # First cell should span 3 rows
        assert table_data.rows[0][0].rowspan == 3
        # Continuation cells should be empty
        assert table_data.rows[1][0].text == ""
        assert table_data.rows[2][0].text == ""

    def test_parse_table_vmerge_ends_mid_table(self, namespaces):
        """Test table where vertical merge ends before last row."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # vMerge for first 2 rows, then normal cell
        # The rowspan update happens in vmerge_info at the end of parsing
        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge w:val="restart"/></w:tcPr>
            <w:p><w:r><w:t>Merged</w:t></w:r></w:p>
        </w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge/></w:tcPr>
            <w:p></w:p>
        </w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:p><w:r><w:t>Normal Cell</w:t></w:r></w:p>
        </w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        assert table_data.row_count == 3
        # Third row has normal cell (no vMerge terminates the previous merge)
        assert table_data.rows[2][0].text == "Normal Cell"
        assert table_data.rows[2][0].is_merged_continuation is False
        # When vMerge ends (no vMerge attribute), the vmerge_info is deleted
        # The rowspan is only updated for merges that are still active at end of parsing

    def test_parse_table_block_empty_table(self, namespaces):
        """Test parse_table_block returns None for empty table."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # Empty table with no rows
        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        result = processor.parse_table_block(tbl)
        assert result is None

    def test_parse_table_block_single_row(self, namespaces):
        """Test parse_table_block with single row (headers only)."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc><w:p><w:r><w:t>Header 1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Header 2</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        result = processor.parse_table_block(tbl)
        assert result is not None
        assert result["type"] == "table"
        assert result["headers"] == ["Header 1", "Header 2"]
        # Single row means rows should be empty after extracting headers
        assert result["rows"] == []

    def test_parse_table_block_with_merged_continuation(self, namespaces):
        """Test parse_table_block skips merged continuation cells."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge w:val="restart"/></w:tcPr>
            <w:p><w:r><w:t>Header</w:t></w:r></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>Col2</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:tcPr><w:vMerge/></w:tcPr>
            <w:p></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>Data</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        result = processor.parse_table_block(tbl)
        assert result is not None
        # Merged continuation cells should be skipped
        assert len(result["headers"]) == 2
        # Second row should only have "Data" (continuation skipped)
        assert result["rows"][0] == ["Data"]

    def test_parse_table_with_multiple_paragraphs(self, namespaces):
        """Test table cell with multiple paragraphs."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:p><w:r><w:t>Line 1</w:t></w:r></w:p>
            <w:p><w:r><w:t>Line 2</w:t></w:r></w:p>
            <w:p><w:r><w:t>Line 3</w:t></w:r></w:p>
        </w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        # Multiple paragraphs should be joined with newlines
        assert "Line 1" in table_data.rows[0][0].text
        assert "Line 2" in table_data.rows[0][0].text
        assert "\n" in table_data.rows[0][0].text

    def test_parse_table_with_empty_paragraphs(self, namespaces):
        """Test table cell with empty paragraphs (should be filtered)."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:p></w:p>
            <w:p><w:r><w:t>Text</w:t></w:r></w:p>
            <w:p></w:p>
        </w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        # Empty paragraphs should be filtered, only "Text" remains
        assert table_data.rows[0][0].text == "Text"

    def test_parse_table_gridspan_with_default_value(self, namespaces):
        """Test gridSpan defaults to 1 when val attribute is missing."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        # gridSpan without val attribute (edge case)
        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:gridSpan/>
            </w:tcPr>
            <w:p><w:r><w:t>Cell</w:t></w:r></w:p>
        </w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        # Should default to colspan=1
        assert table_data.rows[0][0].colspan == 1

    def test_parse_table_complex_merged_structure(self, namespaces):
        """Test complex table with both horizontal and vertical merges."""
        processor = TableProcessor()
        w_ns = namespaces["w"]

        table_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:tbl xmlns:w="{w_ns}">
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:gridSpan w:val="2"/>
                <w:vMerge w:val="restart"/>
            </w:tcPr>
            <w:p><w:r><w:t>Big Cell</w:t></w:r></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>C</w:t></w:r></w:p></w:tc>
    </w:tr>
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:gridSpan w:val="2"/>
                <w:vMerge/>
            </w:tcPr>
            <w:p></w:p>
        </w:tc>
        <w:tc><w:p><w:r><w:t>D</w:t></w:r></w:p></w:tc>
    </w:tr>
</w:tbl>"""
        tbl = ET.fromstring(table_xml)

        table_data = processor.parse_table_data(tbl)
        assert table_data.row_count == 2
        # First cell spans 2 columns and 2 rows
        assert table_data.rows[0][0].colspan == 2
        assert table_data.rows[0][0].rowspan == 2


# ============================================================================
# Extended Coverage Tests for ContentProcessor (73% → 90%)
# ============================================================================


class TestContentProcessorCoverage:
    """Tests to improve ContentProcessor coverage from 73% to 90%."""

    def test_parse_content_with_table(self, namespaces):
        """Test content parsing with embedded table."""
        w_ns = namespaces["w"]

        # Document with table
        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Paragraph before table</w:t></w:r></w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Cell 1</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>Cell 2</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
        <w:p><w:r><w:t>Paragraph after table</w:t></w:r></w:p>
    </w:body>
</w:document>"""

        table_proc = TableProcessor(table_format=TableFormat.MARKDOWN)
        processor = ContentProcessor(table_processor=table_proc)

        result = processor.parse_content(doc_xml, {}, {}, {})
        assert "Paragraph before table" in result
        assert "Cell 1" in result
        assert "Cell 2" in result
        assert "Paragraph after table" in result

    def test_parse_content_blocks_with_table(self, namespaces):
        """Test content blocks parsing with embedded table."""
        w_ns = namespaces["w"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Text</w:t></w:r></w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Header</w:t></w:r></w:p></w:tc>
            </w:tr>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Data</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
    </w:body>
</w:document>"""

        table_proc = TableProcessor()
        processor = ContentProcessor(table_processor=table_proc)

        blocks = processor.parse_content_blocks(doc_xml, {}, {}, {})
        assert len(blocks) >= 2
        # Should have paragraph and table blocks
        assert any(b["type"] == "paragraph" for b in blocks)
        assert any(b["type"] == "table" for b in blocks)

    def test_parse_content_with_image(self, namespaces):
        """Test content parsing with image placeholder."""
        w_ns = namespaces["w"]
        a_ns = namespaces["a"]
        r_ns = namespaces["r"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}" xmlns:a="{a_ns}" xmlns:r="{r_ns}">
    <w:body>
        <w:p>
            <w:r>
                <w:t>Text with image: </w:t>
            </w:r>
            <w:drawing>
                <a:blip r:embed="rId1"/>
            </w:drawing>
        </w:p>
    </w:body>
</w:document>"""

        processor = ContentProcessor(image_placeholder="[IMG_{num}]")
        rid_to_num = {"rId1": 1}

        result = processor.parse_content(doc_xml, rid_to_num, {}, {})
        assert "Text with image:" in result
        assert "[IMG_1]" in result

    def test_parse_content_blocks_pure_image_paragraph(self, namespaces):
        """Test content blocks with paragraph containing only image."""
        w_ns = namespaces["w"]
        a_ns = namespaces["a"]
        r_ns = namespaces["r"]

        # Paragraph with only image (no text)
        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}" xmlns:a="{a_ns}" xmlns:r="{r_ns}">
    <w:body>
        <w:p>
            <w:drawing>
                <a:blip r:embed="rId1"/>
            </w:drawing>
        </w:p>
    </w:body>
</w:document>"""

        processor = ContentProcessor()
        rid_to_num = {"rId1": 42}

        blocks = processor.parse_content_blocks(doc_xml, rid_to_num, {}, {})
        # Should return image block
        assert len(blocks) == 1
        assert blocks[0]["type"] == "image"
        assert blocks[0]["index"] == 42

    def test_parse_content_blocks_empty_paragraph(self, namespaces):
        """Test content blocks with empty paragraph."""
        w_ns = namespaces["w"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p></w:p>
        <w:p>   </w:p>
        <w:p><w:r><w:t>   </w:t></w:r></w:p>
    </w:body>
</w:document>"""

        processor = ContentProcessor()
        blocks = processor.parse_content_blocks(doc_xml, {}, {}, {})
        # Empty paragraphs should return None (filtered out)
        assert len(blocks) == 0

    def test_parse_content_blocks_paragraph_with_inline_image(self, namespaces):
        """Test content blocks with paragraph containing text and inline image."""
        w_ns = namespaces["w"]
        a_ns = namespaces["a"]
        r_ns = namespaces["r"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}" xmlns:a="{a_ns}" xmlns:r="{r_ns}">
    <w:body>
        <w:p>
            <w:r><w:t>See diagram: </w:t></w:r>
            <w:drawing>
                <a:blip r:embed="rId1"/>
            </w:drawing>
            <w:r><w:t> for details.</w:t></w:r>
        </w:p>
    </w:body>
</w:document>"""

        processor = ContentProcessor(image_placeholder="[IMG_{num}]")
        rid_to_num = {"rId1": 5}

        blocks = processor.parse_content_blocks(doc_xml, rid_to_num, {}, {})
        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        # Content should include placeholder
        assert "[IMG_5]" in blocks[0]["content"]

    def test_parse_content_without_table_processor(self, namespaces):
        """Test content parsing without table processor (tables ignored)."""
        w_ns = namespaces["w"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Text</w:t></w:r></w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Table data</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
    </w:body>
</w:document>"""

        # No table_processor
        processor = ContentProcessor(table_processor=None)

        result = processor.parse_content(doc_xml, {}, {}, {})
        assert "Text" in result
        # Table should be ignored
        assert "Table data" not in result

    def test_parse_content_blocks_without_table_processor(self, namespaces):
        """Test content blocks without table processor."""
        w_ns = namespaces["w"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Paragraph</w:t></w:r></w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Ignored</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
    </w:body>
</w:document>"""

        processor = ContentProcessor(table_processor=None)
        blocks = processor.parse_content_blocks(doc_xml, {}, {}, {})

        # Only paragraph block, table ignored
        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"

    def test_parse_content_image_not_in_mapping(self, namespaces):
        """Test image embed ID not in rid_to_num mapping is ignored."""
        w_ns = namespaces["w"]
        a_ns = namespaces["a"]
        r_ns = namespaces["r"]

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}" xmlns:a="{a_ns}" xmlns:r="{r_ns}">
    <w:body>
        <w:p>
            <w:r><w:t>Text</w:t></w:r>
            <w:drawing>
                <a:blip r:embed="rIdUnknown"/>
            </w:drawing>
        </w:p>
    </w:body>
</w:document>"""

        processor = ContentProcessor(image_placeholder="[IMG_{num}]")
        rid_to_num = {"rId1": 1}  # rIdUnknown not in mapping

        result = processor.parse_content(doc_xml, rid_to_num, {}, {})
        # Image should be ignored since not in mapping
        assert "[IMG_" not in result
        assert "Text" in result

    def test_to_text_handles_escaped_chars(self):
        """Test to_text properly removes escaped markdown characters."""
        # to_text unescapes: \\* -> *, \\_ -> _, \\` -> `, \\\\ -> \\
        # Note: \\| is handled differently - | is replaced with space first
        markdown = "Text with \\* asterisk and \\_ underscore"
        text = ContentProcessor.to_text(markdown)

        # Escaped chars should be unescaped
        assert "*" in text
        assert "_" in text
        # Should not have escaped versions
        assert "\\*" not in text
        assert "\\_" not in text

    def test_to_text_handles_br_tags(self):
        """Test to_text converts <br> to newlines."""
        markdown = "Line 1<br>Line 2<br>Line 3"
        text = ContentProcessor.to_text(markdown)

        assert "\n" in text
        assert "<br>" not in text

    def test_to_text_cleans_whitespace(self):
        """Test to_text cleans up extra whitespace."""
        markdown = "Text   with    extra   spaces"
        text = ContentProcessor.to_text(markdown)

        assert "   " not in text

    def test_to_text_cleans_multiple_newlines(self):
        """Test to_text reduces multiple newlines."""
        markdown = "Para 1\n\n\n\n\nPara 2"
        text = ContentProcessor.to_text(markdown)

        assert "\n\n\n" not in text
