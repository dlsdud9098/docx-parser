"""
Pattern-based heading detection strategy.

Detects headings based on text patterns (e.g., "1.", "Chapter 1", "I.").
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Pattern, Tuple

from .base import HeadingContext, HeadingStrategy

logger = logging.getLogger(__name__)


class PatternHeadingStrategy(HeadingStrategy):
    """
    Heading detection based on text patterns.

    This strategy uses compiled regex patterns to detect headings based on
    their text content. Useful for documents that use consistent numbering
    or prefixes for headings.
    """

    def __init__(
        self,
        patterns: List[Tuple[Pattern[str], int]],
        max_heading_level: int = 6,
    ) -> None:
        """
        Initialize with compiled patterns.

        Args:
            patterns: List of (compiled_regex, heading_level) tuples.
            max_heading_level: Maximum allowed heading level.
        """
        self._patterns = patterns
        self._max_heading_level = max_heading_level

    def detect(self, context: HeadingContext) -> Optional[int]:
        """
        Detect heading level based on text patterns.

        Note: This strategy requires the text content to be provided
        separately, as it doesn't extract text from the XML element.
        Use detect_from_text() instead.

        Args:
            context: HeadingContext (element not used for pattern matching).

        Returns:
            None (use detect_from_text for pattern-based detection).
        """
        # Pattern strategy needs text content, not XML element
        # This is handled differently in the parser
        return None

    def detect_from_text(
        self,
        text: str,
        max_heading_level: Optional[int] = None,
    ) -> Optional[int]:
        """
        Detect heading level based on text patterns.

        Args:
            text: Paragraph text to check.
            max_heading_level: Override max heading level (uses instance default if None).

        Returns:
            Heading level (1-max) if pattern matches, None otherwise.
        """
        if not self._patterns or not text:
            return None

        text_stripped = text.strip()
        if not text_stripped:
            return None

        max_level = max_heading_level or self._max_heading_level

        for pattern, level in self._patterns:
            if pattern.match(text_stripped):
                if 1 <= level <= max_level:
                    logger.debug(
                        f"Pattern matched for heading level {level}: "
                        f"{text_stripped[:50]}..."
                    )
                    return level

        return None


def compile_heading_patterns(
    patterns: Optional[List[Tuple[str, int]]],
) -> List[Tuple[Pattern[str], int]]:
    """
    Compile heading patterns to regex patterns.

    Patterns are converted to regex and anchored at the start (^).
    The pattern matching is case-insensitive.

    Args:
        patterns: List of (pattern_string, heading_level) tuples.
            - pattern_string: Regex pattern or simple string
            - heading_level: Heading level (1-9) for matches

    Returns:
        List of (compiled_regex, heading_level) tuples.

    Raises:
        ValueError: If pattern compilation fails.

    Example:
        patterns = [
            (r"Chapter \\d+", 1),  # "Chapter 1", "Chapter 2", etc.
            (r"\\d+\\.", 2),       # "1.", "2.", etc.
            (r"[A-Z]+\\.", 3),     # "A.", "B.", etc.
        ]
    """
    if not patterns:
        return []

    compiled: List[Tuple[Pattern[str], int]] = []

    for pattern_str, level in patterns:
        try:
            # Anchor pattern at start if not already
            if not pattern_str.startswith("^"):
                pattern_str = f"^{pattern_str}"

            compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
            compiled.append((compiled_pattern, level))
            logger.debug(f"Compiled heading pattern: {pattern_str} -> level {level}")
        except re.error as e:
            raise ValueError(f"Invalid heading pattern '{pattern_str}': {e}") from e

    return compiled


def escape_pattern_to_regex(pattern: str) -> str:
    """
    Escape a simple pattern string to regex.

    This is useful for literal string matching where special regex
    characters should be treated as literals.

    Args:
        pattern: Simple pattern string.

    Returns:
        Regex pattern string (anchored at start).
    """
    escaped = re.escape(pattern)
    return f"^{escaped}"
