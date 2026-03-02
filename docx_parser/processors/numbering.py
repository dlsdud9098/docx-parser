"""
Numbering processor for DOCX files.

Handles DOCX list numbering (w:numPr) resolution to text prefixes.
Supports formats: decimal, decimalEnclosedCircle, lowerRoman, upperLetter, bullet, etc.

Also handles w:sym special symbol resolution (e.g., Wingdings font symbols).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple

from ..utils.xml import NAMESPACES

# Circled numbers ①-⑳
_CIRCLED_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

# Wingdings symbol font character mapping to Unicode
# F0xx maps to position 0xxx in the Wingdings font
_WINGDINGS_MAP: Dict[str, str] = {
    # Circled numbers (F081-F08A → ①-⑩)
    "F081": "①",
    "F082": "②",
    "F083": "③",
    "F084": "④",
    "F085": "⑤",
    "F086": "⑥",
    "F087": "⑦",
    "F088": "⑧",
    "F089": "⑨",
    "F08A": "⑩",
    # Arrows
    "F0E0": "→",
    "F0E1": "↔",
    "F0E2": "↑",
    "F0E3": "↓",
    # Common symbols
    "F0FC": "✓",
    "F0FB": "✗",
    "F06C": "●",
    "F06E": "■",
    "F0A8": "◻",
    "F076": "✆",
    "F09F": "•",
}

# Wingdings 2 mapping
_WINGDINGS2_MAP: Dict[str, str] = {
    "F030": "①",
    "F031": "②",
    "F032": "③",
    "F033": "④",
    "F034": "⑤",
    "F035": "⑥",
    "F036": "⑦",
    "F037": "⑧",
    "F038": "⑨",
    "F039": "⑩",
}


def _to_roman(n: int) -> str:
    """Convert integer to Roman numeral string."""
    vals = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    result = ""
    for val, rom in vals:
        while n >= val:
            result += rom
            n -= val
    return result


# Private Use Area (PUA) bullet characters used in DOCX lvlText.
# These are Wingdings-origin characters embedded in numbering.xml.
_PUA_BULLET_MAP: Dict[str, str] = {
    "\uf06c": "●",   # Wingdings 0x6C = filled circle
    "\uf06e": "■",   # Wingdings 0x6E = filled square
    "\uf06f": "□",   # Wingdings 0x6F = empty square
    "\uf075": "◆",   # Wingdings 0x75 = filled diamond
    "\uf09f": "•",   # Wingdings 0x9F = bullet
    "\uf0a7": "■",   # Wingdings 0xA7 = filled square bullet
    "\uf0a8": "◻",   # Wingdings 0xA8 = empty square
    "\uf0b7": "•",   # Symbol 0xB7 = bullet
    "\uf0d8": "▪",   # Wingdings 0xD8 = small filled square
    "\uf0e0": "→",   # Wingdings 0xE0 = right arrow
    "\uf0e8": "↔",   # Wingdings 0xE8 = double arrow
    "\uf0fc": "✓",   # Wingdings 0xFC = checkmark
}


def _normalize_bullet(lvl_text: str) -> str:
    """Replace PUA bullet characters with standard Unicode equivalents."""
    if not lvl_text:
        return lvl_text
    result = []
    for ch in lvl_text:
        result.append(_PUA_BULLET_MAP.get(ch, ch))
    return "".join(result)


def resolve_sym(font: str, char_code: str) -> str:
    """Resolve a w:sym element to its Unicode character.

    Args:
        font: Font name (e.g., "Wingdings", "Wingdings 2").
        char_code: Character code (e.g., "F081").

    Returns:
        Unicode character string, or empty string if unknown.
    """
    code = char_code.upper()
    font_lower = font.lower().strip()

    if font_lower == "wingdings":
        return _WINGDINGS_MAP.get(code, "")
    elif font_lower == "wingdings 2":
        return _WINGDINGS2_MAP.get(code, "")

    return ""


class NumberingResolver:
    """Resolves DOCX list numbering (w:numPr) to text prefixes.

    Parses numbering.xml and tracks sequential counters to produce
    correct numbering prefixes (e.g., "① ", "1. ", "a) ") for each
    paragraph's numId + ilvl combination.

    Must be called in document order for correct counter tracking.
    """

    def __init__(
        self,
        numbering_xml: Optional[str] = None,
        namespaces: Optional[dict] = None,
    ) -> None:
        self._ns = namespaces or NAMESPACES
        # abstractNumId -> {ilvl -> {numFmt, lvlText, start}}
        self._abstract_nums: Dict[str, Dict[str, dict]] = {}
        # numId -> abstractNumId
        self._num_to_abstract: Dict[str, str] = {}
        # numId -> {ilvl -> startOverride}
        self._num_overrides: Dict[str, Dict[str, int]] = {}
        # (numId, ilvl) -> current counter value
        self._counters: Dict[Tuple[str, str], int] = {}

        if numbering_xml:
            self._parse(numbering_xml)

    def _parse(self, numbering_xml: str) -> None:
        """Parse numbering.xml to extract numbering definitions."""
        root = ET.fromstring(numbering_xml)
        w = self._ns["w"]
        w_ns = f"{{{w}}}"

        # Parse abstractNum definitions
        for abstract in root.findall(f".//{w_ns}abstractNum"):
            abs_id = abstract.get(f"{w_ns}abstractNumId")
            levels: Dict[str, dict] = {}

            for lvl in abstract.findall(f"{w_ns}lvl"):
                ilvl = lvl.get(f"{w_ns}ilvl")
                num_fmt_elem = lvl.find(f"{w_ns}numFmt")
                lvl_text_elem = lvl.find(f"{w_ns}lvlText")
                start_elem = lvl.find(f"{w_ns}start")

                levels[ilvl] = {
                    "numFmt": (
                        num_fmt_elem.get(f"{w_ns}val")
                        if num_fmt_elem is not None
                        else "decimal"
                    ),
                    "lvlText": (
                        lvl_text_elem.get(f"{w_ns}val")
                        if lvl_text_elem is not None
                        else "%1."
                    ),
                    "start": (
                        int(start_elem.get(f"{w_ns}val"))
                        if start_elem is not None
                        else 1
                    ),
                }

            self._abstract_nums[abs_id] = levels

        # Parse num -> abstractNum mapping (+ overrides)
        for num in root.findall(f".//{w_ns}num"):
            num_id = num.get(f"{w_ns}numId")
            abs_ref = num.find(f"{w_ns}abstractNumId")
            if abs_ref is not None:
                self._num_to_abstract[num_id] = abs_ref.get(f"{w_ns}val")

            # Check for startOverride
            for override in num.findall(f"{w_ns}lvlOverride"):
                ilvl = override.get(f"{w_ns}ilvl")
                start_override = override.find(f"{w_ns}startOverride")
                if start_override is not None:
                    self._num_overrides.setdefault(num_id, {})[ilvl] = int(
                        start_override.get(f"{w_ns}val", "1")
                    )

    def get_level_info(self, num_id: str, ilvl: str) -> Optional[dict]:
        """Get the numbering level info for given numId and ilvl."""
        abs_id = self._num_to_abstract.get(num_id)
        if not abs_id:
            return None
        levels = self._abstract_nums.get(abs_id, {})
        return levels.get(ilvl)

    def resolve(self, num_id: str, ilvl: str) -> str:
        """Resolve numbering prefix for given numId and ilvl.

        Returns the formatted prefix string (e.g., "① ", "1. ", "a) ").
        Must be called in document order for correct counter tracking.
        """
        level_info = self.get_level_info(num_id, ilvl)
        if not level_info:
            return ""

        num_fmt = level_info["numFmt"]
        lvl_text = level_info["lvlText"]

        # Bullet lists: normalize PUA characters and return
        if num_fmt == "bullet":
            normalized = _normalize_bullet(lvl_text) if lvl_text else "-"
            return normalized + " "

        # Get start value (override takes priority)
        start = level_info["start"]
        overrides = self._num_overrides.get(num_id, {})
        if ilvl in overrides:
            start = overrides[ilvl]

        # Get or initialize counter
        key = (num_id, ilvl)
        if key not in self._counters:
            self._counters[key] = start
        else:
            self._counters[key] += 1

        counter = self._counters[key]

        # Format the number
        formatted = self._format_number(counter, num_fmt)

        # Apply lvlText template ("%1" → "①", "%1." → "1.", "%1)" → "1)")
        prefix = lvl_text
        for i in range(9, 0, -1):
            placeholder = f"%{i}"
            if placeholder in prefix:
                if str(i) == str(int(ilvl) + 1):
                    prefix = prefix.replace(placeholder, formatted)
                else:
                    prefix = prefix.replace(placeholder, "")

        # Add trailing space
        return prefix + " " if prefix else ""

    def _format_number(self, n: int, num_fmt: str) -> str:
        """Format a number according to the numFmt type."""
        if num_fmt == "decimalEnclosedCircle":
            if 1 <= n <= 20:
                return _CIRCLED_NUMBERS[n - 1]
            return f"({n})"  # Fallback for > 20
        elif num_fmt == "decimal":
            return str(n)
        elif num_fmt == "lowerRoman":
            return _to_roman(n).lower()
        elif num_fmt == "upperRoman":
            return _to_roman(n)
        elif num_fmt == "lowerLetter":
            return chr(ord("a") + (n - 1) % 26) if n >= 1 else str(n)
        elif num_fmt == "upperLetter":
            return chr(ord("A") + (n - 1) % 26) if n >= 1 else str(n)
        elif num_fmt == "koreanCounting":
            korean = "일이삼사오육칠팔구십"
            if 1 <= n <= 10:
                return korean[n - 1]
            return str(n)
        elif num_fmt == "ganada":
            ganada = "가나다라마바사아자차카타파하"
            if 1 <= n <= len(ganada):
                return ganada[n - 1]
            return str(n)
        else:
            return str(n)

    def reset(self) -> None:
        """Reset all counters."""
        self._counters.clear()
