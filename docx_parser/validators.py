"""Input validation utilities for docx-parser.

This module provides validation functions for verifying inputs
before processing, helping to catch errors early with clear messages.
"""

from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path
from typing import Optional, Union

from .exceptions import (
    FileNotFoundError,
    InvalidDocxError,
    OutputDirectoryError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# File Validation
# =============================================================================

def validate_docx_file(path: Union[str, Path]) -> Path:
    """Validate that the given path points to a valid DOCX file.

    This function performs the following checks:
    1. The file exists
    2. The file has a .docx extension
    3. The file is a valid ZIP archive
    4. The ZIP contains required DOCX components

    Args:
        path: Path to the DOCX file (string or Path object).

    Returns:
        Path: The validated path as a Path object.

    Raises:
        FileNotFoundError: If the file does not exist.
        InvalidDocxError: If the file is not a valid DOCX.

    Example:
        >>> path = validate_docx_file("document.docx")
        >>> # Raises FileNotFoundError if file doesn't exist
        >>> # Raises InvalidDocxError if not a valid DOCX
    """
    path = Path(path)

    # Check file exists
    if not path.exists():
        raise FileNotFoundError(path)

    # Check extension
    if path.suffix.lower() != ".docx":
        raise InvalidDocxError(
            path=path,
            reason=f"Expected .docx extension, got '{path.suffix}'"
        )

    # Check if it's a valid ZIP file
    if not zipfile.is_zipfile(path):
        raise InvalidDocxError(
            path=path,
            reason="File is not a valid ZIP archive"
        )

    # Check required DOCX components
    required_files = [
        "word/document.xml",
        "[Content_Types].xml",
    ]

    try:
        with zipfile.ZipFile(path, "r") as zf:
            archive_files = zf.namelist()
            for required in required_files:
                if required not in archive_files:
                    raise InvalidDocxError(
                        path=path,
                        reason=f"Missing required component: {required}"
                    )
    except zipfile.BadZipFile as e:
        raise InvalidDocxError(
            path=path,
            reason=f"Corrupted ZIP archive: {e}"
        )

    logger.debug(f"Validated DOCX file: {path}")
    return path


def validate_output_directory(
    path: Optional[Union[str, Path]],
    create: bool = True
) -> Optional[Path]:
    """Validate and optionally create an output directory.

    Args:
        path: Path to the output directory, or None.
        create: Whether to create the directory if it doesn't exist.

    Returns:
        Path: The validated path, or None if path was None.

    Raises:
        OutputDirectoryError: If the directory is invalid or cannot be created.

    Example:
        >>> output_dir = validate_output_directory("./output", create=True)
        >>> # Creates directory if needed and returns Path
    """
    if path is None:
        return None

    path = Path(path)

    if path.exists():
        # Check it's a directory
        if not path.is_dir():
            raise OutputDirectoryError(
                path=path,
                reason="Path exists but is not a directory"
            )

        # Check write permission
        if not os.access(path, os.W_OK):
            raise OutputDirectoryError(
                path=path,
                reason="No write permission"
            )
    else:
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created output directory: {path}")
            except OSError as e:
                raise OutputDirectoryError(
                    path=path,
                    reason=f"Cannot create directory: {e}"
                )
        else:
            raise OutputDirectoryError(
                path=path,
                reason="Directory does not exist"
            )

    return path


# =============================================================================
# Parameter Validation
# =============================================================================

def validate_positive_int(
    value: int,
    parameter: str,
    min_value: int = 1,
    max_value: Optional[int] = None
) -> int:
    """Validate that a value is a positive integer within bounds.

    Args:
        value: The value to validate.
        parameter: Name of the parameter (for error messages).
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive), or None for no limit.

    Returns:
        int: The validated value.

    Raises:
        ValidationError: If the value is out of bounds.

    Example:
        >>> level = validate_positive_int(3, "heading_level", min_value=1, max_value=6)
    """
    if not isinstance(value, int):
        raise ValidationError(
            parameter=parameter,
            value=str(value),
            expected="an integer"
        )

    if value < min_value:
        raise ValidationError(
            parameter=parameter,
            value=str(value),
            expected=f"a value >= {min_value}"
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            parameter=parameter,
            value=str(value),
            expected=f"a value <= {max_value}"
        )

    return value


def validate_enum_value(
    value: Union[str, object],
    enum_class: type,
    parameter: str
) -> object:
    """Validate and convert a value to an enum member.

    Args:
        value: The value to validate (string or enum member).
        enum_class: The enum class to validate against.
        parameter: Name of the parameter (for error messages).

    Returns:
        The enum member.

    Raises:
        ValidationError: If the value is not a valid enum member.

    Example:
        >>> from .config import OutputFormat
        >>> fmt = validate_enum_value("markdown", OutputFormat, "output_format")
    """
    if isinstance(value, enum_class):
        return value

    if isinstance(value, str):
        try:
            return enum_class(value.lower())
        except ValueError:
            valid_values = [e.value for e in enum_class]
            raise ValidationError(
                parameter=parameter,
                value=value,
                expected=f"one of {valid_values}"
            )

    raise ValidationError(
        parameter=parameter,
        value=str(value),
        expected=f"a string or {enum_class.__name__} member"
    )


def validate_string_not_empty(
    value: Optional[str],
    parameter: str,
    allow_none: bool = False
) -> Optional[str]:
    """Validate that a string is not empty.

    Args:
        value: The string value to validate.
        parameter: Name of the parameter (for error messages).
        allow_none: Whether None is an acceptable value.

    Returns:
        The validated string, or None if allowed.

    Raises:
        ValidationError: If the string is empty or None (when not allowed).

    Example:
        >>> title = validate_string_not_empty("My Document", "title")
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(
            parameter=parameter,
            value="None",
            expected="a non-empty string"
        )

    if not isinstance(value, str):
        raise ValidationError(
            parameter=parameter,
            value=str(type(value)),
            expected="a string"
        )

    if not value.strip():
        raise ValidationError(
            parameter=parameter,
            value="''",
            expected="a non-empty string"
        )

    return value


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "validate_docx_file",
    "validate_output_directory",
    "validate_positive_int",
    "validate_enum_value",
    "validate_string_not_empty",
]
