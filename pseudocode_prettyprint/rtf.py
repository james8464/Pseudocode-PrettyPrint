"""RTF rendering for pseudocode tokens."""

from __future__ import annotations

import io
import re
from collections.abc import Sequence
from typing import TextIO

from pseudocode_prettyprint.constants import COLOURS, Colour
from pseudocode_prettyprint.highlight import highlight_tokens
from pseudocode_prettyprint.tokeniser import Token

# RTF colours are 1-indexed; colour 0 is "auto".
_CF: dict[Colour, int] = {
    colour: index + 1 for index, colour in enumerate(COLOURS)
}

_RTF_FOOTER = "}\n"

# Characters that need escaping, or that cannot be written literally in RTF:
# backslash, braces, C0 controls, DEL, and every non-ASCII character.
_RTF_SPECIAL_RE = re.compile(r"[\\{}\x00-\x1f\x7f-\U0010ffff]")


def _signed16(value: int) -> int:
    """RTF \\uN parameters are signed 16-bit values."""
    return value if value < 0x8000 else value - 0x10000


def _unicode_escape(character: str) -> str:
    """Encode one character as one or two RTF \\uN? escapes."""
    codepoint = ord(character)

    # A lone surrogate is not a scalar value and cannot be represented.
    if 0xD800 <= codepoint <= 0xDFFF:
        codepoint = 0xFFFD

    if codepoint > 0xFFFF:
        codepoint -= 0x10000
        high = 0xD800 | (codepoint >> 10)
        low = 0xDC00 | (codepoint & 0x3FF)
        return (
            f"\\u{_signed16(high)}?"
            f"\\u{_signed16(low)}?"
        )

    return f"\\u{_signed16(codepoint)}?"


def _escape_character(character: str) -> str:
    """Escape or encode one character that cannot appear literally in RTF."""
    if character == "\\":
        return "\\\\"
    if character == "{":
        return "\\{"
    if character == "}":
        return "\\}"
    if character == "\n":
        return "\\line\n"
    if character == "\t":
        # \tab is a tab stop; \u9? would be a literal U+0009 character and
        # does not reproduce indentation reliably.
        return "\\tab "
    if character == "\r":
        # Tokenise() normalises CRLF and CR to LF, so this is only a fallback.
        return "\\line\n"
    if character in "\f\v":
        return " "
    if ord(character) < 0x20 or ord(character) == 0x7F:
        # Other control characters have no useful RTF representation; drop
        # them rather than emitting an invalid \uN escape.
        return ""
    return _unicode_escape(character)


def rtf_escape(text: str) -> str:
    """Escape text for RTF, including tabs, newlines and Unicode."""
    if not _RTF_SPECIAL_RE.search(text):
        return text

    parts: list[str] = []
    last = 0
    for match in _RTF_SPECIAL_RE.finditer(text):
        parts.append(text[last:match.start()])
        parts.append(_escape_character(text[match.start()]))
        last = match.end()
    parts.append(text[last:])
    return "".join(parts)


def build_rtf_header() -> str:
    """Build a self-contained RTF header from the colour palette."""
    colour_table = "".join(
        f"\\red{red}\\green{green}\\blue{blue};"
        for red, green, blue in COLOURS.values()
    )
    return (
        "{\\rtf1\\ansi\\deff0\\uc1\n"
        "{\\fonttbl{\\f0\\fmodern\\fprq1\\fcharset0 Menlo;}}\n"
        f"{{\\colortbl;{colour_table}}}\n"
        f"\\pard\\plain\\f0\\fs24\\cf{_CF[Colour.BLACK]}\\b0\\i0\\ul0\n"
    )


def build_rtf_footer() -> str:
    """Return the RTF closing brace."""
    return _RTF_FOOTER


class _RtfRenderer:
    """Stream one token sequence to an RTF stream, tracking formatting state."""

    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = tokens
        self._current_cf: Colour | None = None
        self._current_bold = False

    def _set_cf(self, stream: TextIO, colour: Colour) -> None:
        """Emit a colour change only when the colour actually changes."""
        if self._current_cf != colour:
            stream.write(f"\\cf{_CF[colour]} ")
            self._current_cf = colour

    def _set_bold(self, stream: TextIO, bold: bool) -> None:
        """Emit a bold change only when the weight actually changes."""
        if self._current_bold != bold:
            stream.write("\\b " if bold else "\\b0 ")
            self._current_bold = bold

    def write(self, stream: TextIO) -> None:
        """Write the document body for the configured tokens."""
        self._set_cf(stream, Colour.BLACK)
        self._set_bold(stream, False)

        # Pre-compute highlighting to avoid repeated calls in the loop
        highlighted = highlight_tokens(self._tokens)

        for item in highlighted:
            if item.colour is not None:
                self._set_cf(stream, item.colour)
            self._set_bold(stream, item.bold)
            stream.write(rtf_escape(item.text))
            if item.bold:
                # Reset immediately so the following token starts from a
                # known weight, matching the historical output exactly.
                self._set_bold(stream, False)

        self._set_bold(stream, False)


def render_rtf(tokens: Sequence[Token]) -> str:
    """Render tokens as an RTF document."""
    buffer = io.StringIO()
    write_rtf(tokens, buffer)
    return buffer.getvalue()


def write_rtf(tokens: Sequence[Token], stream: TextIO) -> None:
    """Write a complete RTF document for *tokens* to *stream*."""
    stream.write(build_rtf_header())
    _RtfRenderer(tokens).write(stream)
    stream.write(build_rtf_footer())
