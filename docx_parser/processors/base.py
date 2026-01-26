"""
Base processor protocol and context for DOCX parsing.

This module defines the foundational types used by all processors.
"""

from __future__ import annotations

import logging
import zipfile
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from ..models import ImageInfo, StyleInfo

logger = logging.getLogger(__name__)


@dataclass
class ParsingContext:
    """
    Context object containing shared state for parsing operations.

    This object is passed between processors and maintains state that
    needs to be shared across different processing stages.

    Attributes:
        zip_file: Open ZipFile handle for the DOCX archive.
        styles: Dictionary mapping style IDs to StyleInfo objects.
        font_size_hierarchy: Dictionary mapping font sizes to heading levels.
        images: List of extracted image information.
        rid_to_file: Mapping of relationship IDs to image filenames.
        rid_to_num: Mapping of relationship IDs to image numbers.
        namespaces: XML namespace dictionary.
    """

    zip_file: Optional[zipfile.ZipFile] = None
    styles: Dict[str, StyleInfo] = field(default_factory=dict)
    font_size_hierarchy: Dict[int, int] = field(default_factory=dict)
    images: List[ImageInfo] = field(default_factory=list)
    rid_to_file: Dict[str, str] = field(default_factory=dict)
    rid_to_num: Dict[str, int] = field(default_factory=dict)
    namespaces: Dict[str, str] = field(default_factory=dict)

    # Image extraction results
    image_mapping: Dict[int, str] = field(default_factory=dict)
    images_list: List[ImageInfo] = field(default_factory=list)

    # Additional context
    doc_xml: Optional[str] = None


@runtime_checkable
class Processor(Protocol):
    """
    Base protocol for all processors.

    All processors must implement this protocol, providing a process
    method that takes a context and returns results.
    """

    @abstractmethod
    def process(self, context: ParsingContext, **kwargs: Any) -> Any:
        """
        Process data using the given context.

        Args:
            context: ParsingContext containing shared state.
            **kwargs: Additional processor-specific arguments.

        Returns:
            Processor-specific result type.
        """
        ...
