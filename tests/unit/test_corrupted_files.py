"""
Unit tests for handling corrupted and malformed DOCX files.

These tests verify that the parser handles various edge cases
and error conditions gracefully.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Optional

import pytest

from docx_parser import parse_docx, DocxParser


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def create_minimal_docx(tmp_path):
    """Factory to create minimal DOCX-like ZIP files."""

    def _create(
        content_types: bool = True,
        document_xml: Optional[str] = None,
        core_xml: Optional[str] = None,
        rels_xml: Optional[str] = None,
    ) -> Path:
        path = tmp_path / "test.docx"
        with zipfile.ZipFile(path, "w") as zf:
            if content_types:
                zf.writestr(
                    "[Content_Types].xml",
                    """<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
</Types>"""
                )

            if document_xml is not None:
                zf.writestr("word/document.xml", document_xml)

            if core_xml is not None:
                zf.writestr("docProps/core.xml", core_xml)

            if rels_xml is not None:
                zf.writestr("word/_rels/document.xml.rels", rels_xml)

        return path

    return _create


# ============================================================================
# Invalid File Format Tests
# ============================================================================


class TestInvalidFileFormat:
    """Tests for invalid file formats."""

    def test_not_a_zip_file(self, tmp_path):
        """Test handling of non-ZIP file."""
        path = tmp_path / "not_zip.docx"
        path.write_text("This is plain text, not a ZIP file")

        with pytest.raises(Exception):
            parse_docx(path)

    def test_truncated_zip_file(self, tmp_path):
        """Test handling of truncated ZIP file."""
        path = tmp_path / "truncated.docx"
        # Write partial ZIP header
        path.write_bytes(b"PK\x03\x04" + b"\x00" * 20)

        with pytest.raises(Exception):
            parse_docx(path)

    def test_empty_file(self, tmp_path):
        """Test handling of empty file."""
        path = tmp_path / "empty.docx"
        path.write_bytes(b"")

        with pytest.raises(Exception):
            parse_docx(path)

    def test_binary_garbage(self, tmp_path):
        """Test handling of binary garbage."""
        path = tmp_path / "garbage.docx"
        path.write_bytes(bytes(range(256)) * 4)

        with pytest.raises(Exception):
            parse_docx(path)


# ============================================================================
# Missing Required Files Tests
# ============================================================================


class TestMissingRequiredFiles:
    """Tests for DOCX files missing required components."""

    def test_missing_document_xml(self, create_minimal_docx):
        """Test handling of missing document.xml."""
        path = create_minimal_docx(
            content_types=True,
            document_xml=None,
        )

        with pytest.raises(Exception):
            parse_docx(path)

    def test_missing_content_types(self, tmp_path):
        """Test handling of missing [Content_Types].xml."""
        path = tmp_path / "no_content_types.docx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("word/document.xml", "<document/>")

        # Should still attempt to parse
        # Behavior depends on implementation
        try:
            result = parse_docx(path)
        except Exception:
            pass  # Either way is acceptable


# ============================================================================
# Malformed XML Tests
# ============================================================================


class TestMalformedXML:
    """Tests for malformed XML content."""

    def test_invalid_document_xml(self, create_minimal_docx):
        """Test handling of invalid XML in document.xml."""
        path = create_minimal_docx(
            document_xml="<not valid xml <broken",
        )

        with pytest.raises(Exception):
            parse_docx(path)

    def test_incomplete_document_xml(self, create_minimal_docx):
        """Test handling of incomplete XML."""
        path = create_minimal_docx(
            document_xml="<w:document><w:body>",  # Missing closing tags
        )

        with pytest.raises(Exception):
            parse_docx(path)

    def test_malformed_core_xml(self, create_minimal_docx):
        """Test handling of malformed core.xml structure."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Test</w:t></w:r></w:p>
    </w:body>
</w:document>""",
            # Valid XML but wrong structure for core.xml
            core_xml="""<?xml version="1.0"?><wrong><structure/></wrong>""",
        )

        # Should handle gracefully - core.xml parsing failures shouldn't crash
        result = parse_docx(path, extract_metadata=True)
        # Metadata may be empty but parsing should succeed
        assert result.content

    def test_wrong_namespace_in_document(self, create_minimal_docx):
        """Test handling of wrong XML namespace."""
        path = create_minimal_docx(
            document_xml="""<?xml version="1.0"?>
<document xmlns="wrong:namespace">
    <body>
        <p>Test</p>
    </body>
</document>""",
        )

        # Should handle gracefully with empty content
        result = parse_docx(path)
        # May not find content with wrong namespace


# ============================================================================
# Encoding Issues Tests
# ============================================================================


class TestEncodingIssues:
    """Tests for encoding-related issues."""

    def test_non_utf8_content(self, create_minimal_docx):
        """Test handling of non-UTF8 encoded content."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        # Create a document with Latin-1 encoding declaration but UTF-8 content
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Tes content with special chars: é à ü</w:t></w:r></w:p>
    </w:body>
</w:document>""",
        )

        result = parse_docx(path)
        assert result.content

    def test_unicode_content(self, create_minimal_docx):
        """Test handling of Unicode content."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>한글 日本語 中文 🎉</w:t></w:r></w:p>
    </w:body>
</w:document>""",
        )

        result = parse_docx(path)
        assert "한글" in result.content
        assert "日本語" in result.content


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_paragraphs(self, create_minimal_docx):
        """Test handling of empty paragraphs."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p></w:p>
        <w:p><w:r></w:r></w:p>
        <w:p><w:r><w:t></w:t></w:r></w:p>
        <w:p><w:r><w:t>Actual content</w:t></w:r></w:p>
    </w:body>
</w:document>""",
        )

        result = parse_docx(path)
        assert "Actual content" in result.content

    def test_empty_tables(self, create_minimal_docx):
        """Test handling of empty tables."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:tbl></w:tbl>
        <w:p><w:r><w:t>After empty table</w:t></w:r></w:p>
    </w:body>
</w:document>""",
        )

        result = parse_docx(path)
        assert "After empty table" in result.content

    def test_very_deep_nesting(self, create_minimal_docx):
        """Test handling of deeply nested content."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

        # Create deeply nested structure
        nested = "<w:t>Deep content</w:t>"
        for _ in range(50):
            nested = f"<w:r>{nested}</w:r>"

        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p>{nested}</w:p>
    </w:body>
</w:document>""",
        )

        result = parse_docx(path)
        assert "Deep content" in result.content

    def test_special_characters_in_content(self, create_minimal_docx):
        """Test handling of special characters."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>&lt;tag&gt; &amp; &quot;quotes&quot;</w:t></w:r></w:p>
    </w:body>
</w:document>""",
        )

        result = parse_docx(path)
        assert "<tag>" in result.content
        assert "&" in result.content


# ============================================================================
# Recovery Tests
# ============================================================================


class TestRecovery:
    """Tests for parser recovery from partial failures."""

    def test_missing_optional_metadata(self, create_minimal_docx):
        """Test that missing optional metadata doesn't fail parsing."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Content without metadata</w:t></w:r></w:p>
    </w:body>
</w:document>""",
            core_xml=None,  # No metadata
        )

        result = parse_docx(path, extract_metadata=True)
        assert result.content
        # Metadata should be mostly empty but not cause failure

    def test_missing_relationships(self, create_minimal_docx):
        """Test handling of missing relationship file."""
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        path = create_minimal_docx(
            document_xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{w_ns}">
    <w:body>
        <w:p><w:r><w:t>Content without rels</w:t></w:r></w:p>
    </w:body>
</w:document>""",
            rels_xml=None,  # No relationships
        )

        result = parse_docx(path)
        assert result.content
        assert result.image_count == 0
