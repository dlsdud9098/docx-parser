"""
Base protocol and types for heading detection strategies.

This module defines the HeadingStrategy protocol that all heading detection
strategies must implement.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..models import StyleInfo

logger = logging.getLogger(__name__)


@dataclass
class HeadingContext:
    """
    Context object containing all information needed for heading detection.

    Attributes:
        element: The paragraph XML element to analyze.
        styles: Dictionary mapping style IDs to StyleInfo objects.
        font_size_hierarchy: Dictionary mapping font sizes to heading levels.
        max_heading_level: Maximum allowed heading level (1-6).
        namespaces: XML namespace dictionary.
    """

    element: ET.Element
    styles: Dict[str, "StyleInfo"]
    font_size_hierarchy: Dict[int, int]
    max_heading_level: int
    namespaces: Dict[str, str]

    def get_style_id(self) -> Optional[str]:
        """
        Extract the style ID from the paragraph element.

        Returns:
            Style ID string or None if not found.
        """
        ns = self.namespaces
        w_ns = f"{{{ns['w']}}}"

        pPr = self.element.find(f"{w_ns}pPr", ns)
        if pPr is not None:
            pStyle = pPr.find(f"{w_ns}pStyle", ns)
            if pStyle is not None:
                return pStyle.get(f"{w_ns}val")
        return None


@runtime_checkable
class HeadingStrategy(Protocol):
    """
    Protocol for heading detection strategies.

    All heading detection strategies must implement this protocol,
    providing a method to detect heading level from a paragraph element.
    """

    @abstractmethod
    def detect(self, context: HeadingContext) -> Optional[int]:
        """
        Detect heading level for a paragraph.

        Args:
            context: HeadingContext containing element and style information.

        Returns:
            Heading level (1-6) if detected, None otherwise.
        """
        ...
