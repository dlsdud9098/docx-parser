"""
Integration tests for LangChain document loaders.

Tests DocxDirectLoader and DocxDirectoryLoader with real DOCX files.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from docx_parser.models import HierarchyMode, OutputFormat


# Skip all tests if langchain is not installed
pytest.importorskip("langchain_core", reason="langchain_core not installed")


from docx_parser.langchain_loader import DocxDirectLoader, DocxDirectoryLoader


# ============================================================================
# DocxDirectLoader Tests
# ============================================================================


@pytest.mark.integration
class TestDocxDirectLoader:
    """Tests for DocxDirectLoader."""

    def test_load_simple_document(self, sample_docx):
        """Test loading a simple DOCX file."""
        loader = DocxDirectLoader(sample_docx)
        docs = loader.load()

        assert len(docs) == 1
        doc = docs[0]

        assert doc.page_content
        assert "Test" in doc.page_content or "test" in doc.page_content.lower()

    def test_load_with_metadata(self, sample_docx):
        """Test loading with metadata extraction."""
        loader = DocxDirectLoader(sample_docx, extract_metadata=True)
        docs = loader.load()

        doc = docs[0]
        assert "source" in doc.metadata
        assert doc.metadata["source"] == str(sample_docx)
        assert "file_name" in doc.metadata

    def test_load_with_output_dir(self, sample_docx, output_dir):
        """Test loading with output directory."""
        loader = DocxDirectLoader(sample_docx, output_dir=output_dir)
        docs = loader.load()

        doc = docs[0]
        assert "image_dir" in doc.metadata

    def test_load_markdown_format(self, sample_docx):
        """Test loading with markdown output format."""
        loader = DocxDirectLoader(
            sample_docx,
            output_format=OutputFormat.MARKDOWN
        )
        docs = loader.load()

        assert len(docs) == 1

    def test_load_text_format(self, sample_docx):
        """Test loading with text output format."""
        loader = DocxDirectLoader(
            sample_docx,
            output_format=OutputFormat.TEXT
        )
        docs = loader.load()

        assert len(docs) == 1
        assert docs[0].page_content

    def test_load_with_hierarchy_mode(self, sample_docx_with_headings):
        """Test loading with heading hierarchy detection."""
        loader = DocxDirectLoader(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.STYLE
        )
        docs = loader.load()

        assert len(docs) == 1

    def test_load_with_images(self, sample_docx_with_images, output_dir):
        """Test loading document with images."""
        loader = DocxDirectLoader(
            sample_docx_with_images,
            output_dir=output_dir,
            extract_images=True
        )
        docs = loader.load()

        doc = docs[0]
        assert "[IMAGE_" in doc.page_content

    def test_load_without_image_extraction(self, sample_docx_with_images):
        """Test loading without image extraction."""
        loader = DocxDirectLoader(
            sample_docx_with_images,
            extract_images=False
        )
        docs = loader.load()

        assert len(docs) == 1

    def test_custom_image_placeholder(self, sample_docx_with_images):
        """Test custom image placeholder format."""
        loader = DocxDirectLoader(
            sample_docx_with_images,
            image_placeholder="<<IMG_{num}>>"
        )
        docs = loader.load()

        doc = docs[0]
        # Should use custom placeholder if images present
        assert "<<IMG_" in doc.page_content or "[IMAGE_" not in doc.page_content

    def test_lazy_load(self, sample_docx):
        """Test lazy loading."""
        loader = DocxDirectLoader(sample_docx)
        docs = list(loader.lazy_load())

        assert len(docs) == 1

    def test_string_enum_values(self, sample_docx):
        """Test that string values for enums work."""
        loader = DocxDirectLoader(
            sample_docx,
            output_format="markdown",
            hierarchy_mode="none",
            vertical_merge="repeat",
            horizontal_merge="expand"
        )
        docs = loader.load()

        assert len(docs) == 1


# ============================================================================
# DocxDirectoryLoader Tests
# ============================================================================


@pytest.mark.integration
class TestDocxDirectoryLoader:
    """Tests for DocxDirectoryLoader."""

    def test_load_directory(self, sample_docx, tmp_path):
        """Test loading all DOCX files from a directory."""
        # Create test directory with sample docx
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        # Copy sample docx to test directory
        import shutil
        shutil.copy(sample_docx, doc_dir / "test1.docx")

        loader = DocxDirectoryLoader(doc_dir)
        docs = loader.load()

        assert len(docs) >= 1

    def test_load_empty_directory(self, tmp_path):
        """Test loading from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = DocxDirectoryLoader(empty_dir)
        docs = loader.load()

        assert docs == []

    def test_load_with_glob_pattern(self, sample_docx, tmp_path):
        """Test loading with custom glob pattern."""
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        import shutil
        shutil.copy(sample_docx, doc_dir / "report.docx")

        loader = DocxDirectoryLoader(doc_dir, glob_pattern="*.docx")
        docs = loader.load()

        assert len(docs) >= 1

    def test_lazy_load_directory(self, sample_docx, tmp_path):
        """Test lazy loading from directory."""
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        import shutil
        shutil.copy(sample_docx, doc_dir / "test1.docx")

        loader = DocxDirectoryLoader(doc_dir)
        docs = list(loader.lazy_load())

        assert len(docs) >= 1

    def test_directory_with_output_dir(self, sample_docx, tmp_path, output_dir):
        """Test directory loader with output directory."""
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        import shutil
        shutil.copy(sample_docx, doc_dir / "test1.docx")

        loader = DocxDirectoryLoader(doc_dir, output_dir=output_dir)
        docs = loader.load()

        assert len(docs) >= 1

    def test_directory_with_metadata(self, sample_docx, tmp_path):
        """Test directory loader extracts metadata."""
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        import shutil
        shutil.copy(sample_docx, doc_dir / "test1.docx")

        loader = DocxDirectoryLoader(doc_dir, extract_metadata=True)
        docs = loader.load()

        for doc in docs:
            assert "source" in doc.metadata
            assert "file_name" in doc.metadata


# ============================================================================
# Edge Cases Tests
# ============================================================================


@pytest.mark.integration
class TestEdgeCases:
    """Tests for edge cases."""

    def test_path_as_string(self, sample_docx):
        """Test that string paths work."""
        loader = DocxDirectLoader(str(sample_docx))
        docs = loader.load()

        assert len(docs) == 1

    def test_output_dir_as_string(self, sample_docx, tmp_path):
        """Test that string output_dir works."""
        out_dir = str(tmp_path / "output")
        loader = DocxDirectLoader(sample_docx, output_dir=out_dir)
        docs = loader.load()

        assert len(docs) == 1

    def test_max_heading_level(self, sample_docx_with_headings):
        """Test max_heading_level parameter."""
        loader = DocxDirectLoader(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.STYLE,
            max_heading_level=2
        )
        docs = loader.load()

        assert len(docs) == 1


# ============================================================================
# Additional Coverage Tests
# ============================================================================


@pytest.mark.integration
class TestLoaderCoverageExtended:
    """Extended tests to improve loader code coverage."""

    def test_loader_with_tables_markdown(self, sample_docx_with_tables):
        """Test loader with documents containing tables in markdown format."""
        loader = DocxDirectLoader(
            sample_docx_with_tables,
            output_format=OutputFormat.MARKDOWN
        )
        docs = loader.load()

        assert len(docs) == 1
        # Should contain table content
        assert "Row" in docs[0].page_content or "|" in docs[0].page_content

    def test_loader_text_output_format(self, sample_docx_with_tables):
        """Test loader with text output format."""
        loader = DocxDirectLoader(
            sample_docx_with_tables,
            output_format=OutputFormat.TEXT
        )
        docs = loader.load()

        assert len(docs) == 1
        assert docs[0].page_content

    def test_loader_font_size_hierarchy_mode(self, sample_docx_with_headings):
        """Test loader with font_size hierarchy mode."""
        loader = DocxDirectLoader(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.FONT_SIZE
        )
        docs = loader.load()

        assert len(docs) == 1
        assert docs[0].page_content

    def test_loader_auto_hierarchy_mode(self, sample_docx_with_headings):
        """Test loader with auto hierarchy mode."""
        loader = DocxDirectLoader(
            sample_docx_with_headings,
            hierarchy_mode=HierarchyMode.AUTO
        )
        docs = loader.load()

        assert len(docs) == 1

    def test_loader_all_merge_modes(self, sample_docx_with_tables):
        """Test loader with different merge modes."""
        from docx_parser.models import VerticalMergeMode, HorizontalMergeMode

        # Test all combinations
        for vmerge in [VerticalMergeMode.EMPTY, VerticalMergeMode.FIRST_ONLY]:
            for hmerge in [HorizontalMergeMode.SINGLE, HorizontalMergeMode.REPEAT]:
                loader = DocxDirectLoader(
                    sample_docx_with_tables,
                    vertical_merge=vmerge,
                    horizontal_merge=hmerge
                )
                docs = loader.load()
                assert len(docs) == 1

    def test_directory_recursive_load(self, sample_docx, tmp_path):
        """Test directory loader with nested directories."""
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        sub_dir = doc_dir / "subdir"
        sub_dir.mkdir()

        import shutil
        shutil.copy(sample_docx, doc_dir / "test1.docx")
        shutil.copy(sample_docx, sub_dir / "test2.docx")

        # Load with recursive pattern
        loader = DocxDirectoryLoader(doc_dir, glob_pattern="**/*.docx")
        docs = loader.load()

        assert len(docs) >= 1

    def test_directory_loader_multiple_files(self, sample_docx, sample_docx_with_tables, tmp_path):
        """Test directory loader with multiple DOCX files."""
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        import shutil
        shutil.copy(sample_docx, doc_dir / "doc1.docx")
        shutil.copy(sample_docx_with_tables, doc_dir / "doc2.docx")

        loader = DocxDirectoryLoader(doc_dir, extract_metadata=True)
        docs = loader.load()

        assert len(docs) == 2
        # Check that source paths are different
        sources = [doc.metadata["source"] for doc in docs]
        assert len(set(sources)) == 2

    def test_loader_metadata_content(self, sample_docx):
        """Test that metadata contains expected fields."""
        loader = DocxDirectLoader(sample_docx, extract_metadata=True)
        docs = loader.load()

        doc = docs[0]
        metadata = doc.metadata

        # Check required fields
        assert "source" in metadata
        assert "file_name" in metadata

    def test_loader_with_images_extraction(self, sample_docx_with_images, output_dir):
        """Test loader with image extraction enabled."""
        loader = DocxDirectLoader(
            sample_docx_with_images,
            output_dir=output_dir,
            extract_images=True
        )
        docs = loader.load()

        assert len(docs) == 1
        # Check that images are mentioned in metadata or content
        assert "[IMAGE_" in docs[0].page_content
