"""
XML utilities for docx_parser.

This module contains XML namespace constants and helper functions
for parsing DOCX (Office Open XML) documents.
"""

from __future__ import annotations


# Standard Office Open XML namespaces for document content
NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
}

# Namespaces for document metadata (core properties and extended properties)
METADATA_NAMESPACES = {
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
}


class XMLNamespaces:
    """Helper class for XML namespace operations.

    Provides constants and helper methods for working with
    Office Open XML namespaces.

    Example:
        >>> XMLNamespaces.w_tag('p')
        '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'
        >>> XMLNamespaces.find(root, 'w:p')
        [<Element p ...>]
    """

    # WordprocessingML namespace
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    # DrawingML namespace
    A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    # Relationships namespace
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    # WordprocessingDrawing namespace
    WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
    # Core Properties namespace
    CP = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
    # Dublin Core namespace
    DC = 'http://purl.org/dc/elements/1.1/'
    # Dublin Core Terms namespace
    DCTERMS = 'http://purl.org/dc/terms/'
    # Extended Properties namespace
    EP = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'

    @classmethod
    def w_tag(cls, tag: str) -> str:
        """Create a fully qualified WordprocessingML tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.

        Example:
            >>> XMLNamespaces.w_tag('p')
            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'
        """
        return f"{{{cls.W}}}{tag}"

    @classmethod
    def a_tag(cls, tag: str) -> str:
        """Create a fully qualified DrawingML tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.A}}}{tag}"

    @classmethod
    def r_tag(cls, tag: str) -> str:
        """Create a fully qualified Relationships tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.R}}}{tag}"

    @classmethod
    def wp_tag(cls, tag: str) -> str:
        """Create a fully qualified WordprocessingDrawing tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.WP}}}{tag}"

    @classmethod
    def dc_tag(cls, tag: str) -> str:
        """Create a fully qualified Dublin Core tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.DC}}}{tag}"

    @classmethod
    def dcterms_tag(cls, tag: str) -> str:
        """Create a fully qualified Dublin Core Terms tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.DCTERMS}}}{tag}"

    @classmethod
    def cp_tag(cls, tag: str) -> str:
        """Create a fully qualified Core Properties tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.CP}}}{tag}"

    @classmethod
    def ep_tag(cls, tag: str) -> str:
        """Create a fully qualified Extended Properties tag.

        Args:
            tag: Tag name without namespace prefix.

        Returns:
            Full tag with namespace in Clark notation.
        """
        return f"{{{cls.EP}}}{tag}"

    @classmethod
    def get_all_namespaces(cls) -> dict[str, str]:
        """Get all namespaces as a dictionary.

        Returns:
            Combined dictionary of all namespaces.
        """
        return {**NAMESPACES, **METADATA_NAMESPACES}
