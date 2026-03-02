"""
Processors for DOCX parsing.

This module provides modular processors for different aspects of DOCX parsing:

- MetadataProcessor: Extracts document metadata (author, title, etc.)
- StyleProcessor: Parses styles and builds heading hierarchies
- TableProcessor: Parses and formats tables
- ImageProcessor: Extracts and manages images
- ContentProcessor: Parses document content (paragraphs, headings)

Example:
    from docx_parser.processors import (
        ContentProcessor,
        ImageProcessor,
        MetadataProcessor,
        ParsingContext,
        StyleProcessor,
        TableProcessor,
    )

    # Create context and processors
    context = ParsingContext(zip_file=z)
    metadata_proc = MetadataProcessor()
    style_proc = StyleProcessor()
    image_proc = ImageProcessor()
    table_proc = TableProcessor()
    content_proc = ContentProcessor(table_processor=table_proc)

    # Process in order
    metadata = metadata_proc.process(context, docx_path=path)
    styles = style_proc.process(context)
    images, mapping, img_list = image_proc.process(context, output_dir=out_dir)
    content = content_proc.process(context)
"""

from __future__ import annotations

import logging

from .base import ParsingContext, Processor
from .content import ContentProcessor
from .image import ImageProcessor
from .metadata import MetadataProcessor, extract_metadata
from .numbering import NumberingResolver, resolve_sym
from .style import HeadingDetector, StyleProcessor
from .table import TableProcessor, escape_table_cell

logger = logging.getLogger(__name__)

__all__ = [
    # Base types
    "ParsingContext",
    "Processor",
    # Processors
    "MetadataProcessor",
    "StyleProcessor",
    "TableProcessor",
    "ImageProcessor",
    "ContentProcessor",
    "NumberingResolver",
    # Utilities
    "HeadingDetector",
    "escape_table_cell",
    "extract_metadata",
    "resolve_sym",
]
