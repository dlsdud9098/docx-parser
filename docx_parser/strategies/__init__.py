"""
Heading detection strategies for DOCX parser.

This module provides Strategy Pattern implementations for detecting
heading levels in Word documents. Different strategies are available
for different detection methods:

- StyleHeadingStrategy: Detects headings based on Word styles
- FontSizeHeadingStrategy: Detects headings based on font size
- AutoHeadingStrategy: Combines style and font-size detection
- PatternHeadingStrategy: Detects headings based on text patterns

Example:
    from docx_parser.strategies import get_heading_strategy, HeadingContext
    from docx_parser.models import HierarchyMode

    # Get strategy for a hierarchy mode
    strategy = get_heading_strategy(HierarchyMode.AUTO)

    # Create context and detect heading
    context = HeadingContext(
        element=paragraph_element,
        styles=styles_dict,
        font_size_hierarchy=font_hierarchy,
        max_heading_level=6,
        namespaces=NAMESPACES,
    )

    level = strategy.detect(context)
    if level:
        print(f"Detected heading level: {level}")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Tuple, Type

from ..models import HierarchyMode
from .auto import AutoHeadingStrategy
from .base import HeadingContext, HeadingStrategy
from .font_size import FontSizeHeadingStrategy, build_font_size_hierarchy
from .pattern import (
    PatternHeadingStrategy,
    compile_heading_patterns,
    escape_pattern_to_regex,
)
from .style import StyleHeadingStrategy

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

__all__ = [
    # Base types
    "HeadingContext",
    "HeadingStrategy",
    # Strategies
    "StyleHeadingStrategy",
    "FontSizeHeadingStrategy",
    "AutoHeadingStrategy",
    "PatternHeadingStrategy",
    # Factory
    "get_heading_strategy",
    "HEADING_STRATEGIES",
    # Utilities
    "build_font_size_hierarchy",
    "compile_heading_patterns",
    "escape_pattern_to_regex",
]


# Strategy registry mapping HierarchyMode to strategy classes
HEADING_STRATEGIES: Dict[HierarchyMode, Type[HeadingStrategy]] = {
    HierarchyMode.STYLE: StyleHeadingStrategy,
    HierarchyMode.FONT_SIZE: FontSizeHeadingStrategy,
    HierarchyMode.AUTO: AutoHeadingStrategy,
    # PATTERN is handled separately as it requires configuration
    # NONE returns None (no strategy)
}


class NoneHeadingStrategy(HeadingStrategy):
    """Strategy that never detects headings (for HierarchyMode.NONE)."""

    def detect(self, context: HeadingContext) -> Optional[int]:
        """Always returns None (no heading detection)."""
        return None


def get_heading_strategy(
    mode: HierarchyMode | str,
    patterns: Optional[List[Tuple[Pattern[str], int]]] = None,
    max_heading_level: int = 6,
) -> HeadingStrategy:
    """
    Get a heading strategy for the given hierarchy mode.

    Args:
        mode: The hierarchy mode determining which strategy to use.
        patterns: Compiled patterns for PATTERN mode (required if mode=PATTERN).
        max_heading_level: Maximum heading level for pattern strategy.

    Returns:
        HeadingStrategy instance for the given mode.

    Raises:
        ValueError: If mode is PATTERN but no patterns provided.

    Example:
        # Get style-based strategy
        strategy = get_heading_strategy(HierarchyMode.STYLE)

        # Get pattern-based strategy
        patterns = compile_heading_patterns([("Chapter \\d+", 1)])
        strategy = get_heading_strategy(HierarchyMode.PATTERN, patterns=patterns)
    """
    # Convert string to enum if needed
    if isinstance(mode, str):
        try:
            mode = HierarchyMode(mode)
        except ValueError:
            logger.warning(f"Unknown hierarchy mode '{mode}', using NONE")
            mode = HierarchyMode.NONE

    # Handle NONE mode
    if mode == HierarchyMode.NONE:
        return NoneHeadingStrategy()

    # Handle PATTERN mode
    if mode == HierarchyMode.PATTERN:
        if not patterns:
            raise ValueError(
                "PATTERN mode requires patterns. "
                "Use compile_heading_patterns() to create them."
            )
        return PatternHeadingStrategy(patterns, max_heading_level)

    # Get strategy class from registry
    strategy_cls = HEADING_STRATEGIES.get(mode)
    if strategy_cls is None:
        logger.warning(f"No strategy for mode '{mode}', using NoneHeadingStrategy")
        return NoneHeadingStrategy()

    return strategy_cls()
