"""Custom exceptions for docx-parser.

This module defines a hierarchical exception structure for handling
various error conditions in the docx-parser library.

Exception Hierarchy:
    DocxParserError (base)
    ├── FileError
    │   ├── FileNotFoundError
    │   └── InvalidDocxError
    ├── ParsingError
    │   ├── XMLParsingError
    │   └── ContentParsingError
    ├── ImageProcessingError
    │   ├── ImageExtractionError
    │   └── ImageConversionError
    ├── MetadataExtractionError
    └── ValidationError
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocxParserError(Exception):
    """Base exception for all docx-parser errors.

    All custom exceptions in docx-parser inherit from this class,
    allowing users to catch all library-specific errors with a single except clause.

    Attributes:
        message: Human-readable error message.
        hint: Optional suggestion for resolving the error.
    """

    def __init__(self, message: str, hint: Optional[str] = None) -> None:
        self.message = message
        self.hint = hint

        full_message = message
        if hint:
            full_message = f"{message}\nHint: {hint}"

        super().__init__(full_message)
        logger.error(f"{self.__class__.__name__}: {message}")


# =============================================================================
# File Errors
# =============================================================================

class FileError(DocxParserError):
    """Base exception for file-related errors.

    Attributes:
        path: The file path that caused the error.
    """

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        hint: Optional[str] = None
    ) -> None:
        self.path = path
        super().__init__(message, hint)


class FileNotFoundError(FileError):
    """Raised when the specified DOCX file does not exist.

    Args:
        path: The path to the file that was not found.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(
            message=f"File not found: {path}",
            path=path,
            hint="Verify the file path is correct and the file exists."
        )


class InvalidDocxError(FileError):
    """Raised when the file is not a valid DOCX document.

    This error occurs when:
    - The file is not a valid ZIP archive
    - Required DOCX components are missing (document.xml, etc.)
    - The file is corrupted

    Args:
        path: The path to the invalid file.
        reason: Specific reason why the file is invalid.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.reason = reason
        super().__init__(
            message=f"Invalid DOCX file: {path}\nReason: {reason}",
            path=path,
            hint="Ensure the file is a valid .docx document created by MS Word or compatible software."
        )


# =============================================================================
# Parsing Errors
# =============================================================================

class ParsingError(DocxParserError):
    """Base exception for content parsing errors.

    Attributes:
        component: The DOCX component that failed to parse (e.g., 'document.xml').
    """

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        hint: Optional[str] = None
    ) -> None:
        self.component = component
        super().__init__(message, hint)


class XMLParsingError(ParsingError):
    """Raised when XML parsing fails.

    Args:
        component: The XML file that failed to parse.
        reason: The specific parsing error.
    """

    def __init__(self, component: str, reason: str) -> None:
        self.reason = reason
        super().__init__(
            message=f"Failed to parse XML in '{component}': {reason}",
            component=component,
            hint="The DOCX file may be corrupted or contain malformed XML."
        )


class ContentParsingError(ParsingError):
    """Raised when document content cannot be properly parsed.

    Args:
        component: The content section that failed.
        reason: The specific error reason.
    """

    def __init__(self, component: str, reason: str) -> None:
        self.reason = reason
        super().__init__(
            message=f"Failed to parse content in '{component}': {reason}",
            component=component,
            hint="Some document content may be in an unsupported format."
        )


# =============================================================================
# Image Processing Errors
# =============================================================================

class ImageProcessingError(DocxParserError):
    """Base exception for image processing errors.

    Attributes:
        image_name: The name of the image that caused the error.
    """

    def __init__(
        self,
        message: str,
        image_name: Optional[str] = None,
        hint: Optional[str] = None
    ) -> None:
        self.image_name = image_name
        super().__init__(message, hint)


class ImageExtractionError(ImageProcessingError):
    """Raised when an image cannot be extracted from the DOCX.

    Args:
        image_name: The name of the image in the DOCX archive.
        reason: Why the extraction failed.
    """

    def __init__(self, image_name: str, reason: str) -> None:
        self.reason = reason
        super().__init__(
            message=f"Failed to extract image '{image_name}': {reason}",
            image_name=image_name,
            hint="The image may be corrupted or in an unsupported format."
        )


class ImageConversionError(ImageProcessingError):
    """Raised when image format conversion fails.

    Args:
        image_name: The name of the image being converted.
        source_format: The original image format.
        target_format: The target format for conversion.
        reason: Why the conversion failed.
    """

    def __init__(
        self,
        image_name: str,
        source_format: str,
        target_format: str,
        reason: str
    ) -> None:
        self.source_format = source_format
        self.target_format = target_format
        self.reason = reason
        super().__init__(
            message=(
                f"Failed to convert image '{image_name}' "
                f"from {source_format} to {target_format}: {reason}"
            ),
            image_name=image_name,
            hint=f"Ensure {source_format} format is supported and the image is not corrupted."
        )


# =============================================================================
# Metadata Errors
# =============================================================================

class MetadataExtractionError(DocxParserError):
    """Raised when document metadata cannot be extracted.

    Args:
        field: The metadata field that failed to extract.
        reason: Why the extraction failed.
    """

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(
            message=f"Failed to extract metadata field '{field}': {reason}",
            hint="The document metadata may be missing or malformed."
        )


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(DocxParserError):
    """Raised when input validation fails.

    Args:
        parameter: The parameter that failed validation.
        value: The invalid value.
        expected: Description of what was expected.
    """

    def __init__(self, parameter: str, value: str, expected: str) -> None:
        self.parameter = parameter
        self.value = value
        self.expected = expected
        super().__init__(
            message=f"Invalid value for '{parameter}': got '{value}', expected {expected}",
            hint=f"Provide a valid value for '{parameter}'."
        )


class OutputDirectoryError(DocxParserError):
    """Raised when the output directory is invalid or not writable.

    Args:
        path: The output directory path.
        reason: Why the directory is invalid.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            message=f"Invalid output directory '{path}': {reason}",
            hint="Ensure the directory exists and you have write permissions."
        )


# =============================================================================
# Export all exceptions
# =============================================================================

__all__ = [
    # Base
    "DocxParserError",
    # File errors
    "FileError",
    "FileNotFoundError",
    "InvalidDocxError",
    # Parsing errors
    "ParsingError",
    "XMLParsingError",
    "ContentParsingError",
    # Image errors
    "ImageProcessingError",
    "ImageExtractionError",
    "ImageConversionError",
    # Metadata errors
    "MetadataExtractionError",
    # Validation errors
    "ValidationError",
    "OutputDirectoryError",
]
