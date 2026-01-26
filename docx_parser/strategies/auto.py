"""
Auto heading detection strategy.

Combines style-based and font-size-based detection, trying style first.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import HeadingContext, HeadingStrategy
from .font_size import FontSizeHeadingStrategy
from .style import StyleHeadingStrategy

logger = logging.getLogger(__name__)


class AutoHeadingStrategy(HeadingStrategy):
    """
    Automatic heading detection combining multiple strategies.

    This strategy tries style-based detection first, then falls back to
    font-size-based detection if no heading is found. This provides the
    best coverage for documents that may use either or both methods.
    """

    def __init__(self) -> None:
        """Initialize with sub-strategies."""
        self._style_strategy = StyleHeadingStrategy()
        self._font_size_strategy = FontSizeHeadingStrategy()

    def detect(self, context: HeadingContext) -> Optional[int]:
        """
        Detect heading level using combined strategy.

        Tries style-based detection first, then font-size-based.

        Args:
            context: HeadingContext containing element and style information.

        Returns:
            Heading level (1-max_heading_level) if detected, None otherwise.
        """
        # Try style-based detection first
        level = self._style_strategy.detect(context)
        if level is not None:
            logger.debug(f"Auto strategy: style-based detection returned level {level}")
            return level

        # Fall back to font-size-based detection
        level = self._font_size_strategy.detect(context)
        if level is not None:
            logger.debug(f"Auto strategy: font-size-based detection returned level {level}")
            return level

        return None
