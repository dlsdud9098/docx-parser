"""Tests for docx_parser.models.result module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docx_parser.models.enums import OutputFormat
from docx_parser.models.image import ImageInfo
from docx_parser.models.metadata import AppMetadata, CoreMetadata, DocxMetadata
from docx_parser.models.result import ParseResult


class TestParseResultCreation:
    """Tests for ParseResult creation."""

    def test_minimal_creation(self):
        """Test creating ParseResult with minimal fields."""
        result = ParseResult(content="Hello world")

        assert result.content == "Hello world"
        assert result.images == {}
        assert result.image_mapping == {}
        assert result.source is None
        assert result.image_count == 0
        assert result.output_format == OutputFormat.MARKDOWN

    def test_with_images(self):
        """Test creating ParseResult with images."""
        result = ParseResult(
            content="Doc with [IMAGE_1]",
            images={1: Path("/img/001.png")},
            image_mapping={1: "001.png"},
            image_count=1,
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")]
        )

        assert result.image_count == 1
        assert 1 in result.images
        assert result.images_list[0].name == "001.png"

    def test_with_metadata(self):
        """Test creating ParseResult with metadata."""
        meta = DocxMetadata(
            core=CoreMetadata(title="Test Doc"),
            app=AppMetadata(pages=5)
        )
        result = ParseResult(content="Content", metadata=meta)

        assert result.metadata.core.title == "Test Doc"
        assert result.metadata.app.pages == 5

    def test_with_all_formats(self):
        """Test creating ParseResult with all content formats."""
        result = ParseResult(
            content="# Markdown\n\nParagraph",
            text_content="Markdown\n\nParagraph",
            markdown_content="# Markdown\n\nParagraph",
            output_format=OutputFormat.MARKDOWN
        )

        assert result.text_content == "Markdown\n\nParagraph"
        assert result.markdown_content == "# Markdown\n\nParagraph"


class TestParseResultSaveMethods:
    """Tests for ParseResult save methods."""

    def test_save_markdown(self, tmp_path):
        """Test save_markdown method."""
        result = ParseResult(content="# Title\n\nContent")
        output_path = tmp_path / "output.md"

        saved_path = result.save_markdown(output_path)

        assert saved_path == output_path
        assert output_path.exists()
        assert output_path.read_text() == "# Title\n\nContent"

    def test_save_markdown_creates_directory(self, tmp_path):
        """Test save_markdown creates parent directories."""
        result = ParseResult(content="Test")
        output_path = tmp_path / "nested" / "dir" / "output.md"

        result.save_markdown(output_path)

        assert output_path.exists()

    def test_save_markdown_uses_markdown_content(self, tmp_path):
        """Test save_markdown prefers markdown_content."""
        result = ParseResult(
            content=[{"type": "paragraph", "content": "Block"}],
            markdown_content="# Markdown Version"
        )
        output_path = tmp_path / "output.md"

        result.save_markdown(output_path)

        assert output_path.read_text() == "# Markdown Version"

    def test_save_text(self, tmp_path):
        """Test save_text method."""
        result = ParseResult(
            content="# Markdown",
            text_content="Plain text"
        )
        output_path = tmp_path / "output.txt"

        result.save_text(output_path)

        assert output_path.read_text() == "Plain text"

    def test_save_json(self, tmp_path):
        """Test save_json method."""
        result = ParseResult(
            content="Test content",
            source=Path("/docs/test.docx"),
            image_count=0
        )
        output_path = tmp_path / "output.json"

        result.save_json(output_path)

        data = json.loads(output_path.read_text())
        assert data["content"] == "Test content"
        assert data["source"] == "/docs/test.docx"

    def test_save_mapping(self, tmp_path):
        """Test save_mapping method."""
        result = ParseResult(
            content="Doc",
            image_mapping={1: "001.png", 2: "002.jpg", 3: "003.gif"}
        )
        output_path = tmp_path / "mapping.txt"

        result.save_mapping(output_path)

        content = output_path.read_text()
        assert "[IMAGE_1] -> 001.png" in content
        assert "[IMAGE_2] -> 002.jpg" in content
        assert "[IMAGE_3] -> 003.gif" in content


class TestParseResultImageMethods:
    """Tests for ParseResult image-related methods."""

    def test_get_image_path(self):
        """Test get_image_path method."""
        result = ParseResult(
            content="Doc",
            images={1: Path("/img/001.png"), 2: Path("/img/002.png")}
        )

        assert result.get_image_path(1) == Path("/img/001.png")
        assert result.get_image_path(2) == Path("/img/002.png")
        assert result.get_image_path(3) is None

    def test_replace_placeholders(self):
        """Test replace_placeholders method."""
        result = ParseResult(
            content="Before [IMAGE_1] After",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")]
        )

        replaced = result.replace_placeholders({1: "A beautiful logo"})

        assert "![IMAGE_1](/img/001.png)" in replaced
        assert "A beautiful logo" in replaced
        # Note: the markdown image syntax contains [IMAGE_1] as alt text
        # So we check that the plain placeholder is replaced
        assert "Before [IMAGE_1] After" not in replaced

    def test_replace_placeholders_no_path(self):
        """Test replace_placeholders when image has no path."""
        result = ParseResult(
            content="Text [IMAGE_1] more",
            images_list=[ImageInfo(index=1, name="001.png", path=None)]
        )

        replaced = result.replace_placeholders({1: "Description"})

        assert "[Image: Description]" in replaced

    def test_replace_placeholders_multiple(self):
        """Test replace_placeholders with multiple images."""
        result = ParseResult(
            content="[IMAGE_1] and [IMAGE_2]",
            images_list=[
                ImageInfo(index=1, name="001.png", path="/img/001.png"),
                ImageInfo(index=2, name="002.png", path="/img/002.png")
            ]
        )

        replaced = result.replace_placeholders({
            1: "First image",
            2: "Second image"
        })

        assert "First image" in replaced
        assert "Second image" in replaced


class TestParseResultConversionMethods:
    """Tests for ParseResult conversion methods."""

    def test_to_json_basic(self):
        """Test to_json method."""
        result = ParseResult(
            content="Test",
            source=Path("/test.docx"),
            image_count=0
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["content"] == "Test"
        assert data["source"] == "/test.docx"
        assert data["image_count"] == 0

    def test_to_json_with_images(self):
        """Test to_json includes images list."""
        result = ParseResult(
            content="Doc",
            images_list=[
                ImageInfo(index=1, name="001.png", path="/img/001.png"),
                ImageInfo(index=2, name="002.png", path="/img/002.png")
            ],
            image_count=2
        )

        data = json.loads(result.to_json())

        assert len(data["images"]) == 2
        assert data["images"][0]["name"] == "001.png"

    def test_to_json_with_metadata(self):
        """Test to_json includes metadata."""
        result = ParseResult(
            content="Doc",
            metadata=DocxMetadata(
                core=CoreMetadata(title="Report")
            )
        )

        data = json.loads(result.to_json())

        assert data["metadata"]["title"] == "Report"

    def test_to_langchain_metadata(self):
        """Test to_langchain_metadata method."""
        result = ParseResult(
            content="Test",
            source=Path("/docs/test.docx"),
            image_count=3,
            metadata=DocxMetadata(
                core=CoreMetadata(title="Doc Title"),
                app=AppMetadata(pages=10)
            )
        )

        meta = result.to_langchain_metadata()

        assert meta["source"] == "/docs/test.docx"
        assert meta["file_type"] == "docx"
        assert meta["page"] == 1
        assert meta["image_count"] == 3
        assert meta["title"] == "Doc Title"
        assert meta["total_pages"] == 10

    def test_to_langchain_metadata_with_images(self):
        """Test to_langchain_metadata includes images."""
        result = ParseResult(
            content="Doc",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")],
            image_mapping={1: "001.png"}
        )

        meta = result.to_langchain_metadata()

        assert "images" in meta
        assert meta["image_mapping"] == {1: "001.png"}


class TestParseResultDescribeMethods:
    """Tests for ParseResult describe methods."""

    def test_describe_images_calls_provider(self):
        """Test describe_images calls provider correctly."""
        result = ParseResult(
            content="Doc",
            images_list=[
                ImageInfo(index=1, name="001.png", path="/img/001.png")
            ]
        )

        mock_provider = MagicMock()
        mock_provider.describe_images.return_value = {1: "Description"}

        descriptions = result.describe_images(mock_provider)

        mock_provider.describe_images.assert_called_once()
        assert descriptions == {1: "Description"}

    def test_describe_images_caches_result(self):
        """Test describe_images caches result."""
        result = ParseResult(
            content="Doc",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")]
        )

        mock_provider = MagicMock()
        mock_provider.describe_images.return_value = {1: "Description"}

        result.describe_images(mock_provider)
        result.describe_images(mock_provider)

        # Should only call once due to caching
        assert mock_provider.describe_images.call_count == 1

    def test_describe_images_force_refresh(self):
        """Test describe_images force parameter."""
        result = ParseResult(
            content="Doc",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")],
            image_descriptions={1: "Old"}
        )

        mock_provider = MagicMock()
        mock_provider.describe_images.return_value = {1: "New"}

        descriptions = result.describe_images(mock_provider, force=True)

        assert descriptions == {1: "New"}

    def test_describe_images_empty_list(self):
        """Test describe_images with no images."""
        result = ParseResult(content="No images", images_list=[])

        mock_provider = MagicMock()
        descriptions = result.describe_images(mock_provider)

        assert descriptions == {}
        mock_provider.describe_images.assert_not_called()

    def test_get_described_content_with_provider(self):
        """Test get_described_content with provider."""
        result = ParseResult(
            content="Text [IMAGE_1] more",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")]
        )

        mock_provider = MagicMock()
        mock_provider.describe_images.return_value = {1: "Logo image"}

        content = result.get_described_content(provider=mock_provider)

        assert "Logo image" in content

    def test_get_described_content_with_descriptions(self):
        """Test get_described_content with direct descriptions."""
        result = ParseResult(
            content="Text [IMAGE_1] end",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")]
        )

        content = result.get_described_content(descriptions={1: "Custom desc"})

        assert "Custom desc" in content

    def test_get_described_content_uses_cached(self):
        """Test get_described_content uses cached descriptions."""
        result = ParseResult(
            content="Text [IMAGE_1] end",
            images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")],
            image_descriptions={1: "Cached description"}
        )

        content = result.get_described_content()

        assert "Cached description" in content


class TestParseResultLangChainIntegration:
    """Tests for LangChain integration methods."""

    def test_to_langchain_documents_import_error(self):
        """Test to_langchain_documents raises ImportError."""
        result = ParseResult(content="Test")

        with patch.dict('sys.modules', {'langchain_core': None, 'langchain_core.documents': None}):
            with pytest.raises(ImportError):
                result.to_langchain_documents()

    def test_to_llama_index_documents_import_error(self):
        """Test to_llama_index_documents raises ImportError."""
        result = ParseResult(content="Test")

        with patch.dict('sys.modules', {'llama_index': None, 'llama_index.core': None}):
            with pytest.raises(ImportError):
                result.to_llama_index_documents()

    def test_to_langchain_documents_success(self):
        """Test to_langchain_documents with langchain installed."""
        try:
            from langchain_core.documents import Document
            result = ParseResult(
                content="Test content",
                source=Path("/docs/test.docx"),
                image_count=0
            )

            docs = result.to_langchain_documents()

            assert len(docs) == 1
            assert docs[0].page_content == "Test content"
            assert docs[0].metadata["source"] == "/docs/test.docx"
        except ImportError:
            pytest.skip("langchain not installed")

    def test_to_langchain_documents_with_described(self):
        """Test to_langchain_documents with described=True."""
        try:
            from langchain_core.documents import Document
            result = ParseResult(
                content="Text [IMAGE_1] end",
                images_list=[ImageInfo(index=1, name="001.png", path="/img/001.png")],
                image_descriptions={1: "Logo description"}
            )

            docs = result.to_langchain_documents(described=True)

            assert len(docs) == 1
            assert "Logo description" in docs[0].page_content
        except ImportError:
            pytest.skip("langchain not installed")

    def test_to_langchain_documents_with_list_content(self):
        """Test to_langchain_documents when content is a list (JSON format)."""
        try:
            from langchain_core.documents import Document
            result = ParseResult(
                content=[{"type": "paragraph", "content": "Text"}],
                markdown_content="# Title\n\nText"
            )

            docs = result.to_langchain_documents()

            assert len(docs) == 1
            # Should use markdown_content when content is list
            assert docs[0].page_content == "# Title\n\nText"
        except ImportError:
            pytest.skip("langchain not installed")


class TestParseResultGetDescribedContentExtended:
    """Extended tests for get_described_content method."""

    def test_get_described_content_with_list_content(self):
        """Test get_described_content when content is a list."""
        result = ParseResult(
            content=[{"type": "paragraph", "content": "Text"}],
            markdown_content="# Markdown"
        )

        content = result.get_described_content()

        assert content == "# Markdown"

    def test_get_described_content_with_string_content(self):
        """Test get_described_content when content is a string."""
        result = ParseResult(content="Plain text content")

        content = result.get_described_content()

        assert content == "Plain text content"


class TestParseResultToJsonExtended:
    """Extended tests for to_json method."""

    def test_to_json_with_list_content(self):
        """Test to_json when content is a list (JSON format)."""
        result = ParseResult(
            content=[
                {"type": "paragraph", "content": "First paragraph"},
                {"type": "paragraph", "content": "Second paragraph"}
            ],
            text_content="First paragraph\n\nSecond paragraph"
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        # Should use content as-is when it's a list
        assert isinstance(data["content"], list)
        assert len(data["content"]) == 2

    def test_to_json_with_none_metadata(self):
        """Test to_json when metadata is None."""
        result = ParseResult(content="Test", metadata=None)

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["metadata"] == {}

    def test_to_json_with_none_source(self):
        """Test to_json when source is None."""
        result = ParseResult(content="Test", source=None)

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["source"] is None


class TestParseResultSaveMethodsExtended:
    """Extended tests for save methods."""

    def test_save_text_with_list_content(self, tmp_path):
        """Test save_text when content is a list."""
        result = ParseResult(
            content=[{"type": "paragraph", "content": "Text"}],
            text_content="Plain text version"
        )
        output_path = tmp_path / "output.txt"

        result.save_text(output_path)

        assert output_path.read_text() == "Plain text version"

    def test_save_markdown_with_list_content(self, tmp_path):
        """Test save_markdown when content is a list."""
        result = ParseResult(
            content=[{"type": "paragraph", "content": "Text"}],
            markdown_content="# Markdown version"
        )
        output_path = tmp_path / "output.md"

        result.save_markdown(output_path)

        assert output_path.read_text() == "# Markdown version"

    def test_save_markdown_string_path(self, tmp_path):
        """Test save_markdown with string path."""
        result = ParseResult(content="Test content")
        output_path = str(tmp_path / "output.md")

        saved_path = result.save_markdown(output_path)

        assert Path(output_path).exists()
        assert saved_path == Path(output_path)
