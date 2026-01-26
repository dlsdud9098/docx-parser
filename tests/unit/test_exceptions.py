"""Unit tests for docx_parser.exceptions module.

Tests the custom exception hierarchy and error message formatting.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from docx_parser.exceptions import (
    DocxParserError,
    FileError,
    FileNotFoundError,
    InvalidDocxError,
    ParsingError,
    XMLParsingError,
    ContentParsingError,
    ImageProcessingError,
    ImageExtractionError,
    ImageConversionError,
    MetadataExtractionError,
    ValidationError,
    OutputDirectoryError,
)


class TestDocxParserError:
    """Tests for the base DocxParserError class."""

    def test_basic_message(self) -> None:
        """Test basic error message."""
        error = DocxParserError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.hint is None

    def test_message_with_hint(self) -> None:
        """Test error message with hint."""
        error = DocxParserError("Error occurred", hint="Try this fix")
        assert "Error occurred" in str(error)
        assert "Hint: Try this fix" in str(error)
        assert error.hint == "Try this fix"

    def test_is_exception(self) -> None:
        """Test that DocxParserError is an Exception."""
        error = DocxParserError("Test")
        assert isinstance(error, Exception)


class TestFileErrors:
    """Tests for file-related exceptions."""

    def test_file_error_with_path(self) -> None:
        """Test FileError stores path."""
        path = Path("/some/path.docx")
        error = FileError("File error", path=path)
        assert error.path == path
        assert "File error" in str(error)

    def test_file_not_found_error(self) -> None:
        """Test FileNotFoundError message format."""
        path = Path("/missing/file.docx")
        error = FileNotFoundError(path)
        assert error.path == path
        assert "File not found" in str(error)
        assert str(path) in str(error)
        assert error.hint is not None

    def test_invalid_docx_error(self) -> None:
        """Test InvalidDocxError message format."""
        path = Path("/invalid/file.docx")
        error = InvalidDocxError(path, reason="Not a ZIP file")
        assert error.path == path
        assert error.reason == "Not a ZIP file"
        assert "Invalid DOCX file" in str(error)
        assert "Not a ZIP file" in str(error)
        assert error.hint is not None


class TestParsingErrors:
    """Tests for parsing-related exceptions."""

    def test_parsing_error_with_component(self) -> None:
        """Test ParsingError stores component."""
        error = ParsingError("Parse failed", component="document.xml")
        assert error.component == "document.xml"
        assert "Parse failed" in str(error)

    def test_xml_parsing_error(self) -> None:
        """Test XMLParsingError message format."""
        error = XMLParsingError("styles.xml", reason="Invalid XML syntax")
        assert error.component == "styles.xml"
        assert error.reason == "Invalid XML syntax"
        assert "styles.xml" in str(error)
        assert "Invalid XML syntax" in str(error)

    def test_content_parsing_error(self) -> None:
        """Test ContentParsingError message format."""
        error = ContentParsingError("paragraph", reason="Unknown element")
        assert error.component == "paragraph"
        assert error.reason == "Unknown element"


class TestImageProcessingErrors:
    """Tests for image processing exceptions."""

    def test_image_processing_error_with_name(self) -> None:
        """Test ImageProcessingError stores image name."""
        error = ImageProcessingError("Process failed", image_name="image1.png")
        assert error.image_name == "image1.png"
        assert "Process failed" in str(error)

    def test_image_extraction_error(self) -> None:
        """Test ImageExtractionError message format."""
        error = ImageExtractionError("image1.png", reason="File corrupted")
        assert error.image_name == "image1.png"
        assert error.reason == "File corrupted"
        assert "image1.png" in str(error)
        assert "File corrupted" in str(error)

    def test_image_conversion_error(self) -> None:
        """Test ImageConversionError message format."""
        error = ImageConversionError(
            image_name="image.wdp",
            source_format="WDP",
            target_format="PNG",
            reason="Converter not installed"
        )
        assert error.image_name == "image.wdp"
        assert error.source_format == "WDP"
        assert error.target_format == "PNG"
        assert error.reason == "Converter not installed"
        assert "WDP" in str(error)
        assert "PNG" in str(error)


class TestMetadataExtractionError:
    """Tests for metadata extraction exception."""

    def test_metadata_extraction_error(self) -> None:
        """Test MetadataExtractionError message format."""
        error = MetadataExtractionError("author", reason="Field missing")
        assert error.field == "author"
        assert error.reason == "Field missing"
        assert "author" in str(error)
        assert "Field missing" in str(error)


class TestValidationErrors:
    """Tests for validation exceptions."""

    def test_validation_error(self) -> None:
        """Test ValidationError message format."""
        error = ValidationError(
            parameter="output_format",
            value="invalid",
            expected="one of ['markdown', 'text', 'json']"
        )
        assert error.parameter == "output_format"
        assert error.value == "invalid"
        assert error.expected == "one of ['markdown', 'text', 'json']"
        assert "output_format" in str(error)
        assert "invalid" in str(error)

    def test_output_directory_error(self) -> None:
        """Test OutputDirectoryError message format."""
        path = Path("/readonly/dir")
        error = OutputDirectoryError(path, reason="No write permission")
        assert error.path == path
        assert error.reason == "No write permission"
        assert str(path) in str(error)


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_file_errors_inherit_from_docx_parser_error(self) -> None:
        """Test FileError inherits from DocxParserError."""
        assert issubclass(FileError, DocxParserError)
        assert issubclass(FileNotFoundError, FileError)
        assert issubclass(InvalidDocxError, FileError)

    def test_parsing_errors_inherit_from_docx_parser_error(self) -> None:
        """Test ParsingError inherits from DocxParserError."""
        assert issubclass(ParsingError, DocxParserError)
        assert issubclass(XMLParsingError, ParsingError)
        assert issubclass(ContentParsingError, ParsingError)

    def test_image_errors_inherit_from_docx_parser_error(self) -> None:
        """Test ImageProcessingError inherits from DocxParserError."""
        assert issubclass(ImageProcessingError, DocxParserError)
        assert issubclass(ImageExtractionError, ImageProcessingError)
        assert issubclass(ImageConversionError, ImageProcessingError)

    def test_can_catch_all_with_base_exception(self) -> None:
        """Test all errors can be caught with DocxParserError."""
        exceptions = [
            FileNotFoundError(Path("test")),
            InvalidDocxError(Path("test"), "reason"),
            XMLParsingError("comp", "reason"),
            ImageExtractionError("img", "reason"),
            MetadataExtractionError("field", "reason"),
            ValidationError("param", "val", "expected"),
        ]

        for exc in exceptions:
            with pytest.raises(DocxParserError):
                raise exc
