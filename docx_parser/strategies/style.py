"""
Style-based heading detection strategy.

Detects headings based on Word document styles (e.g., Heading 1, Heading 2).
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import HeadingContext, HeadingStrategy

logger = logging.getLogger(__name__)


class StyleHeadingStrategy(HeadingStrategy):
    """
    Heading detection based on Word document styles.

    This strategy uses the outline level defined in the document's styles.xml
    to determine heading levels. Word built-in heading styles (Heading 1,
    Heading 2, etc.) have outline levels 0-8 which map to heading levels 1-9.
    """

    def detect(self, context: HeadingContext) -> Optional[int]:
        """
        Detect heading level based on paragraph style.

        Args:
            context: HeadingContext containing element and style information.

        Returns:
            Heading level (1-max_heading_level) if style has outline level,
            None otherwise.
        """
        style_id = context.get_style_id()

        if not style_id:
            return None

        if style_id not in context.styles:
            logger.debug(f"Style '{style_id}' not found in styles dictionary")
            return None

        style_info = context.styles[style_id]
        outline_level = style_info.outline_level

        if outline_level is None:
            return None

        # outlineLevel: 0=H1, 1=H2, ..., convert to 1-based
        level = outline_level + 1

        if 1 <= level <= context.max_heading_level:
            logger.debug(
                f"Style '{style_id}' detected as heading level {level}"
            )
            return level

        return None
