"""
Style processing and heading detection for DOCX files.

Handles parsing of styles.xml and font size analysis for heading detection.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from typing import Any, Dict, Optional, Set

from ..models import HierarchyMode, StyleInfo
from ..strategies import (
    HeadingContext,
    HeadingStrategy,
    build_font_size_hierarchy,
    get_heading_strategy,
)
from ..utils.xml import NAMESPACES
from .base import ParsingContext, Processor

logger = logging.getLogger(__name__)


class StyleProcessor(Processor):
    """
    Processor for extracting and analyzing styles from DOCX files.

    Handles:
    - Loading style definitions from styles.xml
    - Collecting font sizes from document
    - Building font size hierarchy for heading detection
    - Creating HeadingStrategy instances
    """

    def __init__(self, namespaces: Optional[dict] = None) -> None:
        """
        Initialize style processor.

        Args:
            namespaces: Optional custom namespace dictionary.
        """
        self._namespaces = namespaces or NAMESPACES

    def process(self, context: ParsingContext, **kwargs: Any) -> Dict[str, StyleInfo]:
        """
        Load styles from the DOCX file.

        Args:
            context: ParsingContext containing the ZipFile.

        Returns:
            Dictionary mapping style IDs to StyleInfo objects.
        """
        if context.zip_file is None:
            return {}
        return self.load_styles(context.zip_file)

    def load_styles(self, z: zipfile.ZipFile) -> Dict[str, StyleInfo]:
        """
        Parse styles.xml and extract style information.

        Args:
            z: Open ZipFile handle.

        Returns:
            Dict mapping style_id to StyleInfo.
        """
        try:
            styles_xml = z.read("word/styles.xml").decode("utf-8")
        except KeyError:
            logger.debug("No styles.xml found in DOCX")
            return {}

        root = ET.fromstring(styles_xml)
        ns = self._namespaces
        w_ns = f"{{{ns['w']}}}"
        styles: Dict[str, StyleInfo] = {}

        for style_elem in root.findall(f".//{w_ns}style", ns):
            style_id = style_elem.get(f"{w_ns}styleId")
            if not style_id:
                continue

            # Get style name
            name_elem = style_elem.find(f"{w_ns}name", ns)
            name = name_elem.get(f"{w_ns}val") if name_elem is not None else None

            # Get outline level (heading level)
            outline_lvl = None
            outline_elem = style_elem.find(f".//{w_ns}outlineLvl", ns)
            if outline_elem is not None:
                val = outline_elem.get(f"{w_ns}val")
                if val and val.isdigit():
                    outline_lvl = int(val)  # 0=H1, 1=H2, ...

            # Get default font size
            font_size = None
            sz_elem = style_elem.find(f".//{w_ns}sz", ns)
            if sz_elem is not None:
                val = sz_elem.get(f"{w_ns}val")
                if val and val.isdigit():
                    font_size = int(val)  # half-points

            styles[style_id] = StyleInfo(
                style_id=style_id,
                name=name,
                outline_level=outline_lvl,
                font_size=font_size,
            )

        logger.debug(f"Loaded {len(styles)} styles from DOCX")
        return styles

    def get_paragraph_font_size(
        self,
        elem: ET.Element,
        styles: Dict[str, StyleInfo],
    ) -> Optional[int]:
        """
        Get the representative font size for a paragraph.

        Priority:
        1. First run's font size (w:r/w:rPr/w:sz)
        2. Paragraph-level font size (w:pPr/w:rPr/w:sz)
        3. Style's default font size

        Args:
            elem: Paragraph XML element.
            styles: Dictionary of style definitions.

        Returns:
            Font size in half-points, or None if not found.
        """
        ns = self._namespaces
        w_ns = f"{{{ns['w']}}}"

        # 1. Check first run's font size
        for run in elem.findall(f"{w_ns}r", ns):
            rPr = run.find(f"{w_ns}rPr", ns)
            if rPr is not None:
                sz = rPr.find(f"{w_ns}sz", ns)
                if sz is not None:
                    val = sz.get(f"{w_ns}val")
                    if val and val.isdigit():
                        return int(val)
            break  # Only check first run

        # 2. Check paragraph-level font size
        pPr = elem.find(f"{w_ns}pPr", ns)
        if pPr is not None:
            rPr = pPr.find(f"{w_ns}rPr", ns)
            if rPr is not None:
                sz = rPr.find(f"{w_ns}sz", ns)
                if sz is not None:
                    val = sz.get(f"{w_ns}val")
                    if val and val.isdigit():
                        return int(val)

            # 3. Check style's default font size
            pStyle = pPr.find(f"{w_ns}pStyle", ns)
            if pStyle is not None:
                style_id = pStyle.get(f"{w_ns}val")
                if style_id and style_id in styles:
                    return styles[style_id].font_size

        return None

    def collect_font_sizes(
        self,
        doc_xml: str,
        styles: Dict[str, StyleInfo],
    ) -> Set[int]:
        """
        Collect all unique font sizes from paragraphs.

        Args:
            doc_xml: Document XML content.
            styles: Dictionary of style definitions.

        Returns:
            Set of unique font sizes (in half-points).
        """
        ns = self._namespaces
        root = ET.fromstring(doc_xml)
        font_sizes: Set[int] = set()

        for para in root.findall(f'.//{{{ns["w"]}}}p', ns):
            size = self.get_paragraph_font_size(para, styles)
            if size:
                font_sizes.add(size)

        return font_sizes

    def get_most_common_font_size(
        self,
        doc_xml: str,
        styles: Dict[str, StyleInfo],
    ) -> Optional[int]:
        """
        Find the most frequently used font size (= body text size).

        Args:
            doc_xml: Document XML content.
            styles: Dictionary of style definitions.

        Returns:
            Most common font size in half-points, or None.
        """
        ns = self._namespaces
        root = ET.fromstring(doc_xml)
        sizes = []

        for para in root.findall(f'.//{{{ns["w"]}}}p', ns):
            size = self.get_paragraph_font_size(para, styles)
            if size:
                sizes.append(size)

        if not sizes:
            return None

        counter = Counter(sizes)
        return counter.most_common(1)[0][0]

    def build_hierarchy(
        self,
        doc_xml: str,
        styles: Dict[str, StyleInfo],
        max_heading_level: int = 6,
    ) -> Dict[int, int]:
        """
        Build font size to heading level mapping.

        Args:
            doc_xml: Document XML content.
            styles: Dictionary of style definitions.
            max_heading_level: Maximum heading depth (1-6).

        Returns:
            Dict mapping font_size (half-points) to heading level (1-6).
        """
        font_sizes = self.collect_font_sizes(doc_xml, styles)
        body_size = self.get_most_common_font_size(doc_xml, styles)

        if not font_sizes or body_size is None:
            return {}

        return build_font_size_hierarchy(
            dict.fromkeys(font_sizes, 1),  # Convert to dict for compatibility
            body_size,
            max_heading_level,
        )


class HeadingDetector:
    """
    Helper class for detecting heading levels in paragraphs.

    Uses the strategy pattern to support different detection methods.
    """

    def __init__(
        self,
        hierarchy_mode: HierarchyMode,
        max_heading_level: int = 6,
        heading_patterns: list = None,
        namespaces: Optional[dict] = None,
    ) -> None:
        """
        Initialize heading detector.

        Args:
            hierarchy_mode: The heading detection mode to use.
            max_heading_level: Maximum heading level (1-6).
            heading_patterns: Compiled patterns for PATTERN mode.
            namespaces: XML namespace dictionary.
        """
        self._hierarchy_mode = hierarchy_mode
        self._max_heading_level = max_heading_level
        self._namespaces = namespaces or NAMESPACES
        self._patterns = heading_patterns

        # Get strategy for non-pattern modes
        if hierarchy_mode != HierarchyMode.PATTERN:
            self._strategy: Optional[HeadingStrategy] = get_heading_strategy(
                hierarchy_mode
            )
        else:
            self._strategy = None

    def detect(
        self,
        elem: ET.Element,
        styles: Dict[str, StyleInfo],
        font_size_hierarchy: Dict[int, int],
        text: Optional[str] = None,
    ) -> Optional[int]:
        """
        Detect heading level for a paragraph.

        Args:
            elem: Paragraph XML element.
            styles: Dictionary of style definitions.
            font_size_hierarchy: Font size to heading level mapping.
            text: Optional text content for pattern-based detection.

        Returns:
            Heading level (1-6) or None if not a heading.
        """
        if self._hierarchy_mode == HierarchyMode.NONE:
            return None

        # Pattern-based detection uses text content
        if self._hierarchy_mode == HierarchyMode.PATTERN:
            return self._detect_by_pattern(text)

        # Use strategy for other modes
        if self._strategy is None:
            return None

        context = HeadingContext(
            element=elem,
            styles=styles,
            font_size_hierarchy=font_size_hierarchy,
            max_heading_level=self._max_heading_level,
            namespaces=self._namespaces,
        )

        return self._strategy.detect(context)

    def _detect_by_pattern(self, text: Optional[str]) -> Optional[int]:
        """
        Detect heading level based on text patterns.

        Args:
            text: Paragraph text to check.

        Returns:
            Heading level (1-max) or None if no pattern matches.
        """
        if not self._patterns or not text:
            return None

        text_stripped = text.strip()
        if not text_stripped:
            return None

        for pattern, level in self._patterns:
            if pattern.match(text_stripped):
                if 1 <= level <= self._max_heading_level:
                    return level

        return None
