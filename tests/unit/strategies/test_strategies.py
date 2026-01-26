"""
Unit tests for heading detection strategies.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Dict
from unittest.mock import MagicMock

import pytest

from docx_parser.models import HierarchyMode, StyleInfo
from docx_parser.strategies import (
    AutoHeadingStrategy,
    FontSizeHeadingStrategy,
    HEADING_STRATEGIES,
    HeadingContext,
    HeadingStrategy,
    PatternHeadingStrategy,
    StyleHeadingStrategy,
    build_font_size_hierarchy,
    compile_heading_patterns,
    escape_pattern_to_regex,
    get_heading_strategy,
)
from docx_parser.utils.xml import NAMESPACES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def namespaces() -> Dict[str, str]:
    """Standard OOXML namespaces."""
    return NAMESPACES


@pytest.fixture
def make_paragraph_element(namespaces):
    """Factory for creating paragraph XML elements."""

    def _make(
        style_id: str | None = None,
        font_size: int | None = None,
        text: str = "Sample text",
    ) -> ET.Element:
        w_ns = namespaces["w"]
        p = ET.Element(f"{{{w_ns}}}p")

        # Add paragraph properties
        if style_id or font_size:
            pPr = ET.SubElement(p, f"{{{w_ns}}}pPr")

            if style_id:
                pStyle = ET.SubElement(pPr, f"{{{w_ns}}}pStyle")
                pStyle.set(f"{{{w_ns}}}val", style_id)

            if font_size:
                rPr = ET.SubElement(pPr, f"{{{w_ns}}}rPr")
                sz = ET.SubElement(rPr, f"{{{w_ns}}}sz")
                sz.set(f"{{{w_ns}}}val", str(font_size))

        # Add run with text
        r = ET.SubElement(p, f"{{{w_ns}}}r")
        t = ET.SubElement(r, f"{{{w_ns}}}t")
        t.text = text

        return p

    return _make


@pytest.fixture
def styles_dict() -> Dict[str, StyleInfo]:
    """Sample styles dictionary."""
    return {
        "Heading1": StyleInfo(style_id="Heading1", name="Heading 1", outline_level=0),
        "Heading2": StyleInfo(style_id="Heading2", name="Heading 2", outline_level=1),
        "Heading3": StyleInfo(style_id="Heading3", name="Heading 3", outline_level=2),
        "Normal": StyleInfo(style_id="Normal", name="Normal", outline_level=None),
        "Title": StyleInfo(style_id="Title", name="Title", font_size=44),
    }


@pytest.fixture
def font_hierarchy() -> Dict[int, int]:
    """Sample font size hierarchy."""
    return {
        44: 1,  # Largest font -> H1
        36: 2,  # Second largest -> H2
        28: 3,  # Third largest -> H3
    }


@pytest.fixture
def heading_context(
    make_paragraph_element, namespaces, styles_dict, font_hierarchy
):
    """Factory for creating HeadingContext."""

    def _make(
        style_id: str | None = None,
        font_size: int | None = None,
        text: str = "Sample text",
        max_heading_level: int = 6,
    ) -> HeadingContext:
        element = make_paragraph_element(style_id, font_size, text)
        return HeadingContext(
            element=element,
            styles=styles_dict,
            font_size_hierarchy=font_hierarchy,
            max_heading_level=max_heading_level,
            namespaces=namespaces,
        )

    return _make


# ============================================================================
# HeadingContext Tests
# ============================================================================


class TestHeadingContext:
    """Tests for HeadingContext dataclass."""

    def test_get_style_id_returns_style(self, heading_context):
        """Test style ID extraction from element."""
        context = heading_context(style_id="Heading1")
        assert context.get_style_id() == "Heading1"

    def test_get_style_id_returns_none_no_style(self, heading_context):
        """Test style ID returns None when no style set."""
        context = heading_context(style_id=None)
        assert context.get_style_id() is None

    def test_context_stores_all_fields(self, heading_context, styles_dict, font_hierarchy):
        """Test context stores all provided fields."""
        context = heading_context(max_heading_level=4)
        assert context.styles == styles_dict
        assert context.font_size_hierarchy == font_hierarchy
        assert context.max_heading_level == 4


# ============================================================================
# StyleHeadingStrategy Tests
# ============================================================================


class TestStyleHeadingStrategy:
    """Tests for StyleHeadingStrategy."""

    def test_detect_heading1(self, heading_context):
        """Test detection of Heading 1 style."""
        strategy = StyleHeadingStrategy()
        context = heading_context(style_id="Heading1")
        assert strategy.detect(context) == 1

    def test_detect_heading2(self, heading_context):
        """Test detection of Heading 2 style."""
        strategy = StyleHeadingStrategy()
        context = heading_context(style_id="Heading2")
        assert strategy.detect(context) == 2

    def test_detect_heading3(self, heading_context):
        """Test detection of Heading 3 style."""
        strategy = StyleHeadingStrategy()
        context = heading_context(style_id="Heading3")
        assert strategy.detect(context) == 3

    def test_returns_none_for_normal_style(self, heading_context):
        """Test Normal style returns None (no outline level)."""
        strategy = StyleHeadingStrategy()
        context = heading_context(style_id="Normal")
        assert strategy.detect(context) is None

    def test_returns_none_for_unknown_style(self, heading_context):
        """Test unknown style returns None."""
        strategy = StyleHeadingStrategy()
        context = heading_context(style_id="UnknownStyle")
        assert strategy.detect(context) is None

    def test_returns_none_for_no_style(self, heading_context):
        """Test no style returns None."""
        strategy = StyleHeadingStrategy()
        context = heading_context(style_id=None)
        assert strategy.detect(context) is None

    def test_respects_max_heading_level(self, heading_context):
        """Test max_heading_level is respected."""
        strategy = StyleHeadingStrategy()
        # Heading3 has outline_level=2 -> level 3
        context = heading_context(style_id="Heading3", max_heading_level=2)
        # Level 3 exceeds max of 2, should return None
        assert strategy.detect(context) is None


# ============================================================================
# FontSizeHeadingStrategy Tests
# ============================================================================


class TestFontSizeHeadingStrategy:
    """Tests for FontSizeHeadingStrategy."""

    def test_detect_largest_font_as_h1(self, heading_context):
        """Test largest font (44) detected as H1."""
        strategy = FontSizeHeadingStrategy()
        context = heading_context(font_size=44)
        assert strategy.detect(context) == 1

    def test_detect_medium_font_as_h2(self, heading_context):
        """Test medium font (36) detected as H2."""
        strategy = FontSizeHeadingStrategy()
        context = heading_context(font_size=36)
        assert strategy.detect(context) == 2

    def test_detect_smaller_font_as_h3(self, heading_context):
        """Test smaller font (28) detected as H3."""
        strategy = FontSizeHeadingStrategy()
        context = heading_context(font_size=28)
        assert strategy.detect(context) == 3

    def test_returns_none_for_body_font(self, heading_context):
        """Test body font size returns None."""
        strategy = FontSizeHeadingStrategy()
        # 22 is not in hierarchy (body text)
        context = heading_context(font_size=22)
        assert strategy.detect(context) is None

    def test_returns_none_for_no_font_size(self, heading_context):
        """Test no font size returns None."""
        strategy = FontSizeHeadingStrategy()
        context = heading_context(font_size=None)
        assert strategy.detect(context) is None


class TestBuildFontSizeHierarchy:
    """Tests for build_font_size_hierarchy function."""

    def test_builds_hierarchy_from_sizes(self):
        """Test hierarchy built correctly from font sizes."""
        font_sizes = {44: 5, 36: 10, 28: 3, 22: 200}
        hierarchy = build_font_size_hierarchy(font_sizes, body_font_size=22)
        assert hierarchy == {44: 1, 36: 2, 28: 3}

    def test_excludes_body_size_and_smaller(self):
        """Test body size and smaller are excluded."""
        font_sizes = {28: 5, 22: 200, 18: 10}
        hierarchy = build_font_size_hierarchy(font_sizes, body_font_size=22)
        assert 22 not in hierarchy
        assert 18 not in hierarchy
        assert hierarchy == {28: 1}

    def test_respects_max_heading_level(self):
        """Test max_heading_level limits hierarchy."""
        font_sizes = {44: 1, 36: 1, 28: 1, 26: 1, 24: 1, 22: 100}
        hierarchy = build_font_size_hierarchy(
            font_sizes, body_font_size=22, max_heading_level=3
        )
        assert len(hierarchy) == 3
        assert hierarchy == {44: 1, 36: 2, 28: 3}

    def test_empty_font_sizes_returns_empty(self):
        """Test empty font sizes returns empty dict."""
        assert build_font_size_hierarchy({}, body_font_size=22) == {}

    def test_no_larger_fonts_returns_empty(self):
        """Test no fonts larger than body returns empty."""
        font_sizes = {22: 100, 18: 50}
        assert build_font_size_hierarchy(font_sizes, body_font_size=22) == {}


# ============================================================================
# AutoHeadingStrategy Tests
# ============================================================================


class TestAutoHeadingStrategy:
    """Tests for AutoHeadingStrategy."""

    def test_prefers_style_over_font_size(self, heading_context):
        """Test style detection is preferred over font size."""
        strategy = AutoHeadingStrategy()
        # Has both Heading1 style and 44pt font
        context = heading_context(style_id="Heading1", font_size=44)
        # Should use style-based level (1) not font-based (1) - same result but style first
        assert strategy.detect(context) == 1

    def test_falls_back_to_font_size(self, heading_context):
        """Test fallback to font size when no style heading."""
        strategy = AutoHeadingStrategy()
        context = heading_context(style_id="Normal", font_size=44)
        assert strategy.detect(context) == 1

    def test_returns_none_when_no_detection(self, heading_context):
        """Test returns None when neither method detects heading."""
        strategy = AutoHeadingStrategy()
        context = heading_context(style_id="Normal", font_size=22)
        assert strategy.detect(context) is None


# ============================================================================
# PatternHeadingStrategy Tests
# ============================================================================


class TestPatternHeadingStrategy:
    """Tests for PatternHeadingStrategy."""

    def test_detect_chapter_pattern(self):
        """Test chapter pattern detection."""
        patterns = compile_heading_patterns([
            (r"Chapter \d+", 1),
        ])
        strategy = PatternHeadingStrategy(patterns)
        assert strategy.detect_from_text("Chapter 1: Introduction") == 1
        assert strategy.detect_from_text("Chapter 42: Conclusion") == 1

    def test_detect_numbered_pattern(self):
        """Test numbered heading pattern."""
        patterns = compile_heading_patterns([
            (r"\d+\.", 2),
        ])
        strategy = PatternHeadingStrategy(patterns)
        assert strategy.detect_from_text("1. First Section") == 2
        assert strategy.detect_from_text("99. Last Section") == 2

    def test_no_match_returns_none(self):
        """Test no pattern match returns None."""
        patterns = compile_heading_patterns([
            (r"Chapter \d+", 1),
        ])
        strategy = PatternHeadingStrategy(patterns)
        assert strategy.detect_from_text("Regular paragraph text") is None

    def test_empty_text_returns_none(self):
        """Test empty text returns None."""
        patterns = compile_heading_patterns([
            (r"Chapter \d+", 1),
        ])
        strategy = PatternHeadingStrategy(patterns)
        assert strategy.detect_from_text("") is None
        assert strategy.detect_from_text("   ") is None

    def test_respects_max_heading_level(self):
        """Test max_heading_level is respected."""
        patterns = compile_heading_patterns([
            (r"Chapter \d+", 5),
        ])
        strategy = PatternHeadingStrategy(patterns, max_heading_level=3)
        assert strategy.detect_from_text("Chapter 1", max_heading_level=3) is None


class TestCompileHeadingPatterns:
    """Tests for compile_heading_patterns function."""

    def test_compiles_simple_pattern(self):
        """Test simple pattern compilation."""
        patterns = compile_heading_patterns([
            ("Chapter", 1),
        ])
        assert len(patterns) == 1
        compiled, level = patterns[0]
        assert level == 1
        assert compiled.match("Chapter 1")

    def test_anchors_pattern_at_start(self):
        """Test pattern is anchored at start."""
        patterns = compile_heading_patterns([
            ("Chapter", 1),
        ])
        compiled, _ = patterns[0]
        assert compiled.match("Chapter 1")
        assert not compiled.match("Introduction Chapter 1")

    def test_handles_already_anchored_pattern(self):
        """Test already anchored pattern is not double-anchored."""
        patterns = compile_heading_patterns([
            ("^Chapter", 1),
        ])
        compiled, _ = patterns[0]
        assert compiled.match("Chapter 1")

    def test_case_insensitive(self):
        """Test patterns are case insensitive."""
        patterns = compile_heading_patterns([
            ("chapter", 1),
        ])
        compiled, _ = patterns[0]
        assert compiled.match("CHAPTER 1")
        assert compiled.match("Chapter 1")
        assert compiled.match("chapter 1")

    def test_empty_patterns_returns_empty(self):
        """Test empty input returns empty list."""
        assert compile_heading_patterns([]) == []
        assert compile_heading_patterns(None) == []

    def test_invalid_pattern_raises_error(self):
        """Test invalid regex raises ValueError."""
        with pytest.raises(ValueError, match="Invalid heading pattern"):
            compile_heading_patterns([
                ("[invalid", 1),  # Invalid regex
            ])


class TestEscapePatternToRegex:
    """Tests for escape_pattern_to_regex function."""

    def test_escapes_special_characters(self):
        """Test special characters are escaped."""
        result = escape_pattern_to_regex("1. Section")
        # re.escape escapes both the dot and the space
        assert result == r"^1\.\ Section"

    def test_anchors_at_start(self):
        """Test result is anchored at start."""
        result = escape_pattern_to_regex("Test")
        assert result.startswith("^")


# ============================================================================
# Strategy Registry Tests
# ============================================================================


class TestHeadingStrategyRegistry:
    """Tests for HEADING_STRATEGIES registry."""

    def test_registry_has_style(self):
        """Test registry has STYLE strategy."""
        assert HierarchyMode.STYLE in HEADING_STRATEGIES
        assert HEADING_STRATEGIES[HierarchyMode.STYLE] == StyleHeadingStrategy

    def test_registry_has_font_size(self):
        """Test registry has FONT_SIZE strategy."""
        assert HierarchyMode.FONT_SIZE in HEADING_STRATEGIES
        assert HEADING_STRATEGIES[HierarchyMode.FONT_SIZE] == FontSizeHeadingStrategy

    def test_registry_has_auto(self):
        """Test registry has AUTO strategy."""
        assert HierarchyMode.AUTO in HEADING_STRATEGIES
        assert HEADING_STRATEGIES[HierarchyMode.AUTO] == AutoHeadingStrategy

    def test_registry_excludes_none_and_pattern(self):
        """Test NONE and PATTERN are not in registry."""
        assert HierarchyMode.NONE not in HEADING_STRATEGIES
        assert HierarchyMode.PATTERN not in HEADING_STRATEGIES


class TestGetHeadingStrategy:
    """Tests for get_heading_strategy factory function."""

    def test_get_style_strategy(self):
        """Test getting style strategy."""
        strategy = get_heading_strategy(HierarchyMode.STYLE)
        assert isinstance(strategy, StyleHeadingStrategy)

    def test_get_font_size_strategy(self):
        """Test getting font size strategy."""
        strategy = get_heading_strategy(HierarchyMode.FONT_SIZE)
        assert isinstance(strategy, FontSizeHeadingStrategy)

    def test_get_auto_strategy(self):
        """Test getting auto strategy."""
        strategy = get_heading_strategy(HierarchyMode.AUTO)
        assert isinstance(strategy, AutoHeadingStrategy)

    def test_get_none_strategy(self):
        """Test getting none strategy."""
        strategy = get_heading_strategy(HierarchyMode.NONE)
        # Should return a strategy that always returns None
        assert isinstance(strategy, HeadingStrategy)

    def test_get_pattern_strategy_with_patterns(self):
        """Test getting pattern strategy with patterns."""
        patterns = compile_heading_patterns([("Chapter", 1)])
        strategy = get_heading_strategy(HierarchyMode.PATTERN, patterns=patterns)
        assert isinstance(strategy, PatternHeadingStrategy)

    def test_get_pattern_strategy_without_patterns_raises(self):
        """Test pattern strategy without patterns raises error."""
        with pytest.raises(ValueError, match="PATTERN mode requires patterns"):
            get_heading_strategy(HierarchyMode.PATTERN)

    def test_accepts_string_mode(self):
        """Test factory accepts string mode."""
        strategy = get_heading_strategy("style")
        assert isinstance(strategy, StyleHeadingStrategy)

    def test_unknown_string_mode_returns_none_strategy(self):
        """Test unknown string mode returns none strategy."""
        strategy = get_heading_strategy("unknown_mode")
        # Should return NoneHeadingStrategy
        assert isinstance(strategy, HeadingStrategy)


# ============================================================================
# Protocol Compliance Tests
# ============================================================================


class TestHeadingStrategyProtocol:
    """Tests for HeadingStrategy protocol compliance."""

    def test_style_strategy_is_heading_strategy(self):
        """Test StyleHeadingStrategy implements protocol."""
        assert isinstance(StyleHeadingStrategy(), HeadingStrategy)

    def test_font_size_strategy_is_heading_strategy(self):
        """Test FontSizeHeadingStrategy implements protocol."""
        assert isinstance(FontSizeHeadingStrategy(), HeadingStrategy)

    def test_auto_strategy_is_heading_strategy(self):
        """Test AutoHeadingStrategy implements protocol."""
        assert isinstance(AutoHeadingStrategy(), HeadingStrategy)

    def test_pattern_strategy_is_heading_strategy(self):
        """Test PatternHeadingStrategy implements protocol."""
        patterns = compile_heading_patterns([("Test", 1)])
        assert isinstance(PatternHeadingStrategy(patterns), HeadingStrategy)
