"""
Content parsing processor for DOCX files.

Handles parsing document content including paragraphs, images, and text.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from ..models import (
    HeadingBlock,
    HierarchyMode,
    ImageBlock,
    OutputFormat,
    ParagraphBlock,
    StyleInfo,
)
from ..utils.xml import NAMESPACES
from .base import ParsingContext, Processor
from .numbering import NumberingResolver, resolve_sym
from .style import HeadingDetector
from .table import TableProcessor

logger = logging.getLogger(__name__)


class ContentProcessor(Processor):
    """
    Processor for parsing document content from DOCX files.

    Handles:
    - Parsing paragraphs with text and images
    - Detecting headings based on styles or font sizes
    - Converting to markdown or structured blocks
    """

    def __init__(
        self,
        hierarchy_mode: HierarchyMode = HierarchyMode.NONE,
        max_heading_level: int = 6,
        heading_patterns: Optional[list] = None,
        image_placeholder: str = "[IMAGE_{num}]",
        output_format: OutputFormat = OutputFormat.MARKDOWN,
        table_processor: Optional[TableProcessor] = None,
        namespaces: Optional[dict] = None,
    ) -> None:
        """
        Initialize content processor.

        Args:
            hierarchy_mode: How to detect heading hierarchy.
            max_heading_level: Maximum heading level (1-6).
            heading_patterns: Compiled patterns for pattern-based detection.
            image_placeholder: Format string for image placeholders.
            output_format: Output format (markdown, text, json).
            table_processor: TableProcessor instance for table parsing.
            namespaces: Optional custom namespace dictionary.
        """
        self._hierarchy_mode = hierarchy_mode
        self._max_heading_level = max_heading_level
        self._image_placeholder = image_placeholder
        self._output_format = output_format
        self._namespaces = namespaces or NAMESPACES
        self._table_processor = table_processor
        self._numbering: Optional[NumberingResolver] = None

        # Create heading detector
        self._heading_detector = HeadingDetector(
            hierarchy_mode=hierarchy_mode,
            max_heading_level=max_heading_level,
            heading_patterns=heading_patterns,
            namespaces=self._namespaces,
        )

    def set_numbering(self, numbering: NumberingResolver) -> None:
        """Set the numbering resolver for list numbering support."""
        self._numbering = numbering

    def process(
        self,
        context: ParsingContext,
        **kwargs: Any,
    ) -> str:
        """
        Parse document content to markdown.

        Args:
            context: ParsingContext containing document XML and mappings.

        Returns:
            Parsed content string.
        """
        if context.doc_xml is None:
            return ""

        return self.parse_content(
            context.doc_xml,
            context.rid_to_num,
            context.styles,
            context.font_size_hierarchy,
        )

    def parse_content(
        self,
        doc_xml: str,
        rid_to_num: Dict[str, int],
        styles: Optional[Dict[str, StyleInfo]] = None,
        font_size_hierarchy: Optional[Dict[int, int]] = None,
    ) -> str:
        """
        Parse document.xml to extract text with image placeholders.

        Args:
            doc_xml: Document XML content.
            rid_to_num: Mapping of relationship IDs to image numbers.
            styles: Dictionary of style definitions.
            font_size_hierarchy: Font size to heading level mapping.

        Returns:
            Parsed content string.
        """
        ns = self._namespaces
        root = ET.fromstring(doc_xml)
        result = []

        styles = styles or {}
        font_size_hierarchy = font_size_hierarchy or {}

        for body in root.findall(".//w:body", ns):
            for elem in body:
                if elem.tag == f"{{{ns['w']}}}p":
                    para_text = self._parse_paragraph(
                        elem, rid_to_num, styles, font_size_hierarchy
                    )
                    if para_text:
                        result.append(para_text)

                elif elem.tag == f"{{{ns['w']}}}tbl":
                    if self._table_processor:
                        table_text = self._table_processor.parse_table(elem, rid_to_num)
                        if table_text:
                            result.append(table_text)

        return "\n\n".join(result)

    def parse_content_blocks(
        self,
        doc_xml: str,
        rid_to_num: Dict[str, int],
        styles: Optional[Dict[str, StyleInfo]] = None,
        font_size_hierarchy: Optional[Dict[int, int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parse document.xml to extract structured content blocks for JSON output.

        Args:
            doc_xml: Document XML content.
            rid_to_num: Mapping of relationship IDs to image numbers.
            styles: Dictionary of style definitions.
            font_size_hierarchy: Font size to heading level mapping.

        Returns:
            List of content block dictionaries.
        """
        ns = self._namespaces
        root = ET.fromstring(doc_xml)
        blocks: List[Dict[str, Any]] = []

        styles = styles or {}
        font_size_hierarchy = font_size_hierarchy or {}

        for body in root.findall(".//w:body", ns):
            for elem in body:
                if elem.tag == f"{{{ns['w']}}}p":
                    block = self._parse_paragraph_block(
                        elem, rid_to_num, styles, font_size_hierarchy
                    )
                    if block:
                        blocks.append(block)

                elif elem.tag == f"{{{ns['w']}}}tbl":
                    if self._table_processor:
                        block = self._table_processor.parse_table_block(elem, rid_to_num)
                        if block:
                            blocks.append(block)

        return blocks

    def _parse_paragraph(
        self,
        elem: ET.Element,
        rid_to_num: Dict[str, int],
        styles: Dict[str, StyleInfo],
        font_size_hierarchy: Dict[int, int],
    ) -> str:
        """
        Parse a paragraph element with optional heading detection.

        Args:
            elem: Paragraph XML element.
            rid_to_num: Mapping of relationship IDs to image numbers.
            styles: Dictionary of style definitions.
            font_size_hierarchy: Font size to heading level mapping.

        Returns:
            Parsed paragraph text.
        """
        ns = self._namespaces
        para_text = []

        for child in elem.iter():
            # Text
            if child.tag == f"{{{ns['w']}}}t" and child.text:
                para_text.append(child.text)

            # Special symbol (w:sym) — e.g., Wingdings ①②③
            elif child.tag == f"{{{ns['w']}}}sym":
                font = child.get(f"{{{ns['w']}}}font", "")
                char_code = child.get(f"{{{ns['w']}}}char", "")
                resolved = resolve_sym(font, char_code)
                if resolved:
                    para_text.append(resolved)

            # Image (blip in drawing)
            elif child.tag == f"{{{ns['a']}}}blip":
                embed = child.get(f"{{{ns['r']}}}embed")
                if embed and embed in rid_to_num:
                    num = rid_to_num[embed]
                    placeholder = self._image_placeholder.format(num=num)
                    para_text.append(placeholder)

        text = "".join(para_text)

        # Prepend list numbering prefix (e.g., "① ", "1. ")
        numbering_prefix = self._resolve_numbering(elem)
        if numbering_prefix:
            text = numbering_prefix + text

        # Apply heading markup if hierarchy detection is enabled
        if self._hierarchy_mode != HierarchyMode.NONE and text.strip():
            heading_level = self._heading_detector.detect(
                elem, styles, font_size_hierarchy, text
            )

            if heading_level:
                prefix = "#" * heading_level + " "
                return prefix + text

        return text

    def _resolve_numbering(self, elem: ET.Element) -> str:
        """Extract numbering prefix from paragraph properties.

        Reads w:numPr (numId + ilvl) and resolves via NumberingResolver.
        """
        if not self._numbering:
            return ""

        ns = self._namespaces
        pPr = elem.find(f"{{{ns['w']}}}pPr")
        if pPr is None:
            return ""

        numPr = pPr.find(f"{{{ns['w']}}}numPr")
        if numPr is None:
            return ""

        numId_elem = numPr.find(f"{{{ns['w']}}}numId")
        ilvl_elem = numPr.find(f"{{{ns['w']}}}ilvl")

        if numId_elem is None:
            return ""

        num_id = numId_elem.get(f"{{{ns['w']}}}val", "0")
        ilvl = ilvl_elem.get(f"{{{ns['w']}}}val", "0") if ilvl_elem is not None else "0"

        # numId="0" means no numbering
        if num_id == "0":
            return ""

        return self._numbering.resolve(num_id, ilvl)

    def _parse_paragraph_block(
        self,
        elem: ET.Element,
        rid_to_num: Dict[str, int],
        styles: Dict[str, StyleInfo],
        font_size_hierarchy: Dict[int, int],
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a paragraph element to a content block.

        Args:
            elem: Paragraph XML element.
            rid_to_num: Mapping of relationship IDs to image numbers.
            styles: Dictionary of style definitions.
            font_size_hierarchy: Font size to heading level mapping.

        Returns:
            Content block dictionary or None if empty.
        """
        ns = self._namespaces
        para_parts = []
        image_indices = []

        for child in elem.iter():
            # Text
            if child.tag == f"{{{ns['w']}}}t" and child.text:
                para_parts.append(("text", child.text))

            # Special symbol (w:sym) — e.g., Wingdings ①②③
            elif child.tag == f"{{{ns['w']}}}sym":
                font = child.get(f"{{{ns['w']}}}font", "")
                char_code = child.get(f"{{{ns['w']}}}char", "")
                resolved = resolve_sym(font, char_code)
                if resolved:
                    para_parts.append(("text", resolved))

            # Image (blip in drawing)
            elif child.tag == f"{{{ns['a']}}}blip":
                embed = child.get(f"{{{ns['r']}}}embed")
                if embed and embed in rid_to_num:
                    num = rid_to_num[embed]
                    image_indices.append(num)
                    para_parts.append(("image", num))

        # Get text content
        text_content = "".join(part[1] for part in para_parts if part[0] == "text")

        # Prepend list numbering prefix
        numbering_prefix = self._resolve_numbering(elem)
        if numbering_prefix:
            text_content = numbering_prefix + text_content

        # Pure image paragraph
        if not text_content.strip() and image_indices:
            return ImageBlock(index=image_indices[0]).to_dict()

        # Empty paragraph
        if not text_content.strip():
            return None

        # Check if it's a heading
        if self._hierarchy_mode != HierarchyMode.NONE:
            heading_level = self._heading_detector.detect(
                elem, styles, font_size_hierarchy, text_content
            )
            if heading_level:
                return HeadingBlock(content=text_content, level=heading_level).to_dict()

        # Regular paragraph (may contain inline images as placeholders)
        content = text_content
        if image_indices:
            content = "".join(
                part[1]
                if part[0] == "text"
                else self._image_placeholder.format(num=part[1])
                for part in para_parts
            )

        return ParagraphBlock(content=content).to_dict()

    @staticmethod
    def to_text(markdown_content: str) -> str:
        """
        Convert markdown to plain text.

        Args:
            markdown_content: Markdown content.

        Returns:
            Plain text content.
        """
        text = markdown_content
        # Remove markdown table formatting
        text = re.sub(r"\|", " ", text)
        text = re.sub(r"-{3,}", "", text)
        # Remove escaped characters
        text = re.sub(r"\\([|*_`\\])", r"\1", text)
        # Remove <br> tags
        text = re.sub(r"<br>", "\n", text)
        # Clean up extra whitespace
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
