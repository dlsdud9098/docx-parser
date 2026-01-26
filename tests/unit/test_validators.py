"""Unit tests for docx_parser.validators module.

Tests input validation functions.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from docx_parser.validators import (
    validate_docx_file,
    validate_output_directory,
    validate_positive_int,
    validate_enum_value,
    validate_string_not_empty,
)
from docx_parser.exceptions import (
    FileNotFoundError,
    InvalidDocxError,
    OutputDirectoryError,
    ValidationError,
)
from docx_parser.config import OutputFormat


class TestValidateDocxFile:
    """Tests for validate_docx_file function."""

    def test_valid_docx(self, sample_docx: Path) -> None:
        """Test validation passes for valid DOCX."""
        result = validate_docx_file(sample_docx)
        assert result == sample_docx
        assert isinstance(result, Path)

    def test_string_path_converted_to_path(self, sample_docx: Path) -> None:
        """Test string path is converted to Path."""
        result = validate_docx_file(str(sample_docx))
        assert isinstance(result, Path)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test raises FileNotFoundError for missing file."""
        missing = tmp_path / "missing.docx"
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_docx_file(missing)
        assert exc_info.value.path == missing

    def test_wrong_extension(self, tmp_path: Path) -> None:
        """Test raises InvalidDocxError for wrong extension."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("content")
        with pytest.raises(InvalidDocxError) as exc_info:
            validate_docx_file(txt_file)
        assert "extension" in exc_info.value.reason.lower()

    def test_not_a_zip_file(self, non_docx_file: Path) -> None:
        """Test raises InvalidDocxError for non-ZIP file."""
        with pytest.raises(InvalidDocxError) as exc_info:
            validate_docx_file(non_docx_file)
        assert "ZIP" in exc_info.value.reason

    def test_missing_document_xml(self, tmp_path: Path) -> None:
        """Test raises InvalidDocxError for DOCX without document.xml."""
        import zipfile

        invalid = tmp_path / "invalid.docx"
        with zipfile.ZipFile(invalid, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
            # Missing word/document.xml

        with pytest.raises(InvalidDocxError) as exc_info:
            validate_docx_file(invalid)
        assert "document.xml" in exc_info.value.reason


class TestValidateOutputDirectory:
    """Tests for validate_output_directory function."""

    def test_none_returns_none(self) -> None:
        """Test None input returns None."""
        assert validate_output_directory(None) is None

    def test_existing_directory(self, tmp_path: Path) -> None:
        """Test validation passes for existing writable directory."""
        result = validate_output_directory(tmp_path)
        assert result == tmp_path

    def test_string_path_converted(self, tmp_path: Path) -> None:
        """Test string path is converted to Path."""
        result = validate_output_directory(str(tmp_path))
        assert isinstance(result, Path)

    def test_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """Test creates directory when create=True."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        assert not new_dir.exists()

        result = validate_output_directory(new_dir, create=True)
        assert result == new_dir
        assert new_dir.exists()

    def test_raises_if_missing_and_no_create(self, tmp_path: Path) -> None:
        """Test raises error when create=False and dir missing."""
        missing = tmp_path / "missing"
        with pytest.raises(OutputDirectoryError) as exc_info:
            validate_output_directory(missing, create=False)
        assert "does not exist" in exc_info.value.reason

    def test_raises_if_path_is_file(self, tmp_path: Path) -> None:
        """Test raises error when path is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(OutputDirectoryError) as exc_info:
            validate_output_directory(file_path)
        assert "not a directory" in exc_info.value.reason


class TestValidatePositiveInt:
    """Tests for validate_positive_int function."""

    def test_valid_value(self) -> None:
        """Test validation passes for valid value."""
        assert validate_positive_int(5, "level") == 5

    def test_min_value(self) -> None:
        """Test validation with min_value."""
        assert validate_positive_int(3, "level", min_value=1) == 3

        with pytest.raises(ValidationError) as exc_info:
            validate_positive_int(0, "level", min_value=1)
        assert "level" in str(exc_info.value)

    def test_max_value(self) -> None:
        """Test validation with max_value."""
        assert validate_positive_int(5, "level", max_value=6) == 5

        with pytest.raises(ValidationError) as exc_info:
            validate_positive_int(7, "level", max_value=6)
        assert "level" in str(exc_info.value)

    def test_non_integer_raises(self) -> None:
        """Test raises for non-integer value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_int("five", "level")  # type: ignore
        assert "integer" in exc_info.value.expected


class TestValidateEnumValue:
    """Tests for validate_enum_value function."""

    def test_valid_string(self) -> None:
        """Test validation passes for valid string."""
        result = validate_enum_value("markdown", OutputFormat, "format")
        assert result == OutputFormat.MARKDOWN

    def test_valid_enum_member(self) -> None:
        """Test validation passes for enum member."""
        result = validate_enum_value(OutputFormat.JSON, OutputFormat, "format")
        assert result == OutputFormat.JSON

    def test_case_insensitive(self) -> None:
        """Test string validation is case-insensitive."""
        result = validate_enum_value("MARKDOWN", OutputFormat, "format")
        assert result == OutputFormat.MARKDOWN

    def test_invalid_string_raises(self) -> None:
        """Test raises for invalid string value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_enum_value("invalid", OutputFormat, "format")
        assert "format" in str(exc_info.value)
        assert "markdown" in exc_info.value.expected.lower()

    def test_invalid_type_raises(self) -> None:
        """Test raises for invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            validate_enum_value(123, OutputFormat, "format")  # type: ignore
        assert "format" in str(exc_info.value)


class TestValidateStringNotEmpty:
    """Tests for validate_string_not_empty function."""

    def test_valid_string(self) -> None:
        """Test validation passes for non-empty string."""
        assert validate_string_not_empty("hello", "title") == "hello"

    def test_string_with_whitespace(self) -> None:
        """Test validation passes for string with content."""
        assert validate_string_not_empty("  hello  ", "title") == "  hello  "

    def test_empty_string_raises(self) -> None:
        """Test raises for empty string."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_not_empty("", "title")
        assert "title" in str(exc_info.value)
        assert "non-empty" in exc_info.value.expected

    def test_whitespace_only_raises(self) -> None:
        """Test raises for whitespace-only string."""
        with pytest.raises(ValidationError):
            validate_string_not_empty("   ", "title")

    def test_none_raises_by_default(self) -> None:
        """Test raises for None by default."""
        with pytest.raises(ValidationError):
            validate_string_not_empty(None, "title")

    def test_none_allowed(self) -> None:
        """Test None is allowed when allow_none=True."""
        assert validate_string_not_empty(None, "title", allow_none=True) is None

    def test_non_string_raises(self) -> None:
        """Test raises for non-string value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_not_empty(123, "title")  # type: ignore
        assert "string" in exc_info.value.expected
