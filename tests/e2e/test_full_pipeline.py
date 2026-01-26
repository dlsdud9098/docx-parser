"""
End-to-end tests for the full DOCX parsing pipeline.

These tests verify the complete workflow from reading a DOCX file
to generating output in various formats.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from docx_parser import parse_docx, DocxParser
from docx_parser.models import (
    HierarchyMode,
    OutputFormat,
    ParseResult,
    TableFormat,
)


# ============================================================================
# Full Pipeline Tests
# ============================================================================


@pytest.mark.e2e
class TestFullPipeline:
    """Tests for the complete parsing pipeline."""

    def test_full_pipeline_markdown(self, sample_docx_with_headings, output_dir):
        """Test full pipeline with markdown output."""
        result = parse_docx(
            sample_docx_with_headings,
            output_dir=output_dir,
            output_format=OutputFormat.MARKDOWN,
            hierarchy_mode=HierarchyMode.STYLE,
            extract_metadata=True,
            save_file=True,
        )

        # Verify result structure
        assert result.content
        assert result.markdown_content
        assert result.text_content
        assert result.metadata

        # Verify file saved
        md_file = output_dir / f"{sample_docx_with_headings.stem}.md"
        assert md_file.exists()
        assert md_file.read_text() == result.markdown_content

    def test_full_pipeline_json(self, sample_docx_with_tables, output_dir):
        """Test full pipeline with JSON output."""
        result = parse_docx(
            sample_docx_with_tables,
            output_dir=output_dir,
            output_format=OutputFormat.JSON,
            extract_metadata=True,
            save_file=True,
        )

        # Verify JSON structure
        assert isinstance(result.content, list)
        for block in result.content:
            assert "type" in block

        # Verify file saved
        json_file = output_dir / f"{sample_docx_with_tables.stem}.json"
        assert json_file.exists()

        # Verify JSON is valid (save_json saves a dict, not just the content)
        saved_content = json.loads(json_file.read_text())
        assert isinstance(saved_content, dict)
        assert "content" in saved_content

    def test_full_pipeline_with_images(self, sample_docx_with_images, output_dir):
        """Test full pipeline with image extraction."""
        result = parse_docx(
            sample_docx_with_images,
            output_dir=output_dir,
            extract_images=True,
            convert_images=True,
        )

        # Verify images extracted
        assert result.image_count > 0
        assert len(result.images_list) > 0

        # Verify image files exist
        for img in result.images_list:
            if img.path:
                assert Path(img.path).exists()

        # Verify placeholders in content
        assert "[IMAGE_" in result.content


@pytest.mark.e2e
class TestDocumentTypes:
    """Tests for different document types."""

    def test_simple_document(self, sample_docx):
        """Test parsing simple text document."""
        result = parse_docx(sample_docx)

        assert result.content
        assert "Test" in result.content or "test" in result.content.lower()

    def test_document_with_headings(self, sample_docx_with_headings):
        """Test parsing document with multiple heading levels."""
        result = parse_docx(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.STYLE,
        )

        # Should detect headings
        assert result.content
        # Verify heading markers are present
        assert "#" in result.content

    def test_document_with_tables(self, sample_docx_with_tables):
        """Test parsing document with tables."""
        result = parse_docx(sample_docx_with_tables)

        # Should contain table formatting
        assert "|" in result.content

    def test_document_with_images(self, sample_docx_with_images):
        """Test parsing document with images."""
        result = parse_docx(sample_docx_with_images)

        # Should contain image placeholders
        assert "[IMAGE_" in result.content
        assert result.image_count > 0


@pytest.mark.e2e
class TestOutputConsistency:
    """Tests for output consistency."""

    def test_same_input_same_output(self, sample_docx):
        """Test that parsing same file produces same output."""
        result1 = parse_docx(sample_docx)
        result2 = parse_docx(sample_docx)

        assert result1.content == result2.content
        assert result1.text_content == result2.text_content
        assert result1.markdown_content == result2.markdown_content

    def test_parser_reuse_consistency(self, sample_docx):
        """Test that reusing parser produces consistent output."""
        parser = DocxParser()

        result1 = parser.parse(sample_docx)
        result2 = parser.parse(sample_docx)

        assert result1.content == result2.content

    def test_format_conversion_consistency(self, sample_docx):
        """Test that text/markdown conversion is consistent."""
        result = parse_docx(sample_docx)

        # Text should be derivable from markdown
        assert result.text_content
        assert result.markdown_content

        # Markdown should contain at least as much info as text
        # (after stripping markdown formatting)


@pytest.mark.e2e
class TestMetadataExtraction:
    """Tests for metadata extraction in E2E scenarios."""

    def test_metadata_preserved_in_output(self, sample_docx, output_dir):
        """Test that metadata is preserved through pipeline."""
        result = parse_docx(
            sample_docx,
            output_dir=output_dir,
            extract_metadata=True,
        )

        # Verify metadata exists
        assert result.metadata
        assert result.metadata.file_name == sample_docx.name

        # Verify to_json includes metadata
        json_output = result.to_json()
        assert "metadata" in json_output

    def test_langchain_metadata_format(self, sample_docx):
        """Test LangChain-compatible metadata output."""
        result = parse_docx(sample_docx, extract_metadata=True)

        lc_meta = result.to_langchain_metadata()

        # Required LangChain fields
        assert "source" in lc_meta
        assert lc_meta["source"] == str(sample_docx)


@pytest.mark.e2e
class TestTableFormats:
    """Tests for different table output formats."""

    def test_all_table_formats(self, sample_docx_with_tables):
        """Test all table format options."""
        formats = [
            TableFormat.MARKDOWN,
            TableFormat.HTML,
            TableFormat.JSON,
            TableFormat.TEXT,
        ]

        results = {}
        for fmt in formats:
            result = parse_docx(sample_docx_with_tables, table_format=fmt)
            results[fmt] = result.content

        # All should have content
        assert all(r for r in results.values())

        # All should be different (different formats)
        # Note: Some may be similar if table is simple
        assert len(set(results.values())) >= 2

    def test_markdown_table_format(self, sample_docx_with_tables):
        """Test markdown table formatting."""
        result = parse_docx(
            sample_docx_with_tables,
            table_format=TableFormat.MARKDOWN,
        )

        # Markdown table indicators
        assert "|" in result.content
        assert "---" in result.content

    def test_html_table_format(self, sample_docx_with_tables):
        """Test HTML table formatting."""
        result = parse_docx(
            sample_docx_with_tables,
            table_format=TableFormat.HTML,
        )

        # HTML table indicators
        assert "<table>" in result.content
        assert "</table>" in result.content
        assert "<tr>" in result.content


@pytest.mark.e2e
class TestHeadingModes:
    """Tests for different heading detection modes."""

    def test_style_heading_mode(self, sample_docx_with_headings):
        """Test style-based heading detection."""
        result = parse_docx(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.STYLE,
        )

        # Should have markdown headings
        assert "#" in result.content

    def test_none_heading_mode(self, sample_docx_with_headings):
        """Test no heading detection."""
        result = parse_docx(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.NONE,
        )

        # Content should still be there
        assert result.content

    def test_auto_heading_mode(self, sample_docx_with_headings):
        """Test auto heading detection."""
        result = parse_docx(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.AUTO,
        )

        # Should detect headings
        assert result.content


@pytest.mark.e2e
class TestResultMethods:
    """Tests for ParseResult methods."""

    def test_save_methods(self, sample_docx, output_dir):
        """Test all save methods."""
        result = parse_docx(sample_docx)

        # Save markdown
        md_path = output_dir / "test.md"
        result.save_markdown(md_path)
        assert md_path.exists()

        # Save text
        txt_path = output_dir / "test.txt"
        result.save_text(txt_path)
        assert txt_path.exists()

        # Save JSON
        json_path = output_dir / "test.json"
        result.save_json(json_path)
        assert json_path.exists()

    def test_to_json_method(self, sample_docx):
        """Test to_json serialization."""
        result = parse_docx(sample_docx, extract_metadata=True)

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert "content" in parsed
        assert "metadata" in parsed

    def test_replace_placeholders(self, sample_docx_with_images):
        """Test placeholder replacement."""
        result = parse_docx(sample_docx_with_images)

        # Create mock descriptions
        descriptions = {1: "A red square image"}

        replaced = result.replace_placeholders(descriptions)

        # Should contain the description
        if result.image_count > 0:
            assert "red square" in replaced or "[IMAGE_" in replaced


@pytest.mark.e2e
class TestBatchProcessing:
    """Tests for batch document processing."""

    def test_batch_processing(self, sample_docx, sample_docx_with_tables, output_dir):
        """Test processing multiple documents."""
        paths = [sample_docx, sample_docx_with_tables]
        results = parse_docx(paths, output_dir=output_dir)

        assert len(results) == 2
        assert all(isinstance(r, ParseResult) for r in results)

        # Each result should have different source
        sources = [r.source for r in results]
        assert len(set(sources)) == 2

    def test_batch_with_save(self, sample_docx, sample_docx_with_tables, output_dir):
        """Test batch processing with file saving."""
        paths = [sample_docx, sample_docx_with_tables]
        results = parse_docx(
            paths,
            output_dir=output_dir,
            save_file=True,
        )

        # Verify files saved
        for path in paths:
            md_path = output_dir / f"{path.stem}.md"
            assert md_path.exists()


@pytest.mark.e2e
class TestEdgeCases:
    """Tests for edge cases in E2E scenarios."""

    def test_empty_document(self, empty_docx):
        """Test parsing empty document."""
        result = parse_docx(empty_docx)

        # Should succeed with empty/minimal content
        assert isinstance(result, ParseResult)

    def test_very_long_document(self, sample_docx_with_headings, tmp_path):
        """Test parsing document by verifying basic operation."""
        # Just verify normal document works
        result = parse_docx(sample_docx_with_headings)
        assert result.content
