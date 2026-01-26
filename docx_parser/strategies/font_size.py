"""
Font-size-based heading detection strategy.

Detects headings based on font size relative to body text.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from .base import HeadingContext, HeadingStrategy

logger = logging.getLogger(__name__)


class FontSizeHeadingStrategy(HeadingStrategy):
    """
    Heading detection based on font size hierarchy.

    This strategy uses a pre-computed font size hierarchy that maps
    font sizes (in half-points) to heading levels. Only font sizes
    larger than the body text are considered as potential headings.
    """

    def detect(self, context: HeadingContext) -> Optional[int]:
        """
        Detect heading level based on paragraph font size.

        Args:
            context: HeadingContext containing element and font size hierarchy.

        Returns:
            Heading level (1-max_heading_level) if font size indicates heading,
            None otherwise.
        """
        font_size = self._get_paragraph_font_size(context)

        if font_size is None:
            return None

        if font_size not in context.font_size_hierarchy:
            return None

        level = context.font_size_hierarchy[font_size]
        logger.debug(f"Font size {font_size} detected as heading level {level}")
        return level

    def _get_paragraph_font_size(self, context: HeadingContext) -> Optional[int]:
        """
        Get the font size for a paragraph element.

        Args:
            context: HeadingContext containing the paragraph element.

        Returns:
            Font size in half-points, or None if not specified.
        """
        ns = context.namespaces
        w_ns = f"{{{ns['w']}}}"
        element = context.element

        # Check paragraph properties first
        pPr = element.find(f"{w_ns}pPr", ns)
        if pPr is not None:
            rPr = pPr.find(f"{w_ns}rPr", ns)
            if rPr is not None:
                sz = rPr.find(f"{w_ns}sz", ns)
                if sz is not None:
                    val = sz.get(f"{w_ns}val")
                    if val and val.isdigit():
                        return int(val)

        # Check first run's font size as fallback
        for run in element.findall(f".//{w_ns}r", ns):
            rPr = run.find(f"{w_ns}rPr", ns)
            if rPr is not None:
                sz = rPr.find(f"{w_ns}sz", ns)
                if sz is not None:
                    val = sz.get(f"{w_ns}val")
                    if val and val.isdigit():
                        return int(val)
            break  # Only check first run

        # Try style-based font size
        style_id = context.get_style_id()
        if style_id and style_id in context.styles:
            style_info = context.styles[style_id]
            if style_info.font_size is not None:
                return style_info.font_size

        return None


def build_font_size_hierarchy(
    font_sizes: Dict[int, int],
    body_font_size: int,
    max_heading_level: int = 6,
) -> Dict[int, int]:
    """
    Build a font size to heading level mapping.

    Only font sizes larger than body_font_size become headings.
    Larger fonts get lower heading levels (H1 is largest).

    Args:
        font_sizes: Dictionary of font_size -> occurrence_count.
        body_font_size: The most common font size (assumed to be body text).
        max_heading_level: Maximum heading depth (1-6).

    Returns:
        Dict mapping font_size (half-points) to heading level (1-max).

    Example:
        font_sizes = {28: 5, 24: 10, 22: 200, 20: 3}
        body_font_size = 22
        # Returns: {28: 1, 24: 2} (22 and 20 are body text or smaller)
    """
    if not font_sizes or body_font_size <= 0:
        return {}

    # Only sizes larger than body text can be headings
    heading_sizes = [
        size for size in font_sizes.keys() if size > body_font_size
    ]

    if not heading_sizes:
        return {}

    # Sort descending - largest font = H1
    sorted_sizes = sorted(heading_sizes, reverse=True)

    hierarchy = {}
    for level, size in enumerate(sorted_sizes[:max_heading_level], start=1):
        hierarchy[size] = level

    logger.debug(f"Built font size hierarchy: {hierarchy}")
    return hierarchy
