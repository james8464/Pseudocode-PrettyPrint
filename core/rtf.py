"""RTF rendering for pseudocode tokens."""

from __future__ import annotations

from collections.abc import Sequence
import io
import re
from typing import TextIO

from core.constants import COLOURS, Colour
from core.tokeniser import Token, TokenKind, is_keyword

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
    return _RTF_FOOTER


def _next_non_ws_indices(tokens: Sequence[Token]) -> list[int | None]:
    """For each token, the index of the next non-whitespace token (or None)."""
    next_indices: list[int | None] = [None] * len(tokens)
    next_index: int | None = None
    for index in range(len(tokens) - 1, -1, -1):
        next_indices[index] = next_index
        if tokens[index].kind is not TokenKind.WS:
            next_index = index
    return next_indices


# Identifiers introduced by these keywords are callable/type names.  This is
# a small declaration-aware symbol table, not a capitalisation heuristic.
_DECLARATION_KEYWORDS = frozenset({
    "PROCEDURE", "FUNCTION", "TYPE", "CLASS", "NEW", "INHERITS",
})


def _find_callables(
    tokens: Sequence[Token],
    next_non_ws: Sequence[int | None],
) -> frozenset[str]:
    callables: set[str] = set()
    for index, token in enumerate(tokens):
        if (
            token.kind is TokenKind.IDENT
            and token.text.upper() in _DECLARATION_KEYWORDS
        ):
            next_index = next_non_ws[index]
            if next_index is not None:
                next_token = tokens[next_index]
                if next_token.kind is TokenKind.IDENT:
                    callables.add(next_token.text.casefold())
    return frozenset(callables)


class _RtfRenderer:
    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = tokens
        self._next_non_ws = _next_non_ws_indices(tokens)
        self._callables = _find_callables(tokens, self._next_non_ws)
        self._current_cf: Colour | None = None
        self._current_bold = False

    def _set_cf(self, stream: TextIO, colour: Colour) -> None:
        if self._current_cf != colour:
            stream.write(f"\\cf{_CF[colour]} ")
            self._current_cf = colour

    def _set_bold(self, stream: TextIO, bold: bool) -> None:
        if self._current_bold != bold:
            stream.write("\\b " if bold else "\\b0 ")
            self._current_bold = bold

    def write(self, stream: TextIO) -> None:
        self._set_cf(stream, Colour.BLACK)
        self._set_bold(stream, False)

        after_dot = False
        after_call_kw = False
        after_import = False

        for index, token in enumerate(self._tokens):
            kind = token.kind
            text = token.text

            if kind is TokenKind.WS:
                stream.write(rtf_escape(text))
                # A dot cannot continue a member chain across whitespace.
                after_dot = False
                # A CALL or IMPORT does not continue across a line break.
                if "\n" in text:
                    after_call_kw = False
                    after_import = False
                continue

            if kind is TokenKind.COMMENT:
                self._set_cf(stream, Colour.COMMENT)
                self._set_bold(stream, False)
                stream.write(rtf_escape(text))
                after_dot = after_call_kw = after_import = False
                continue

            if kind is TokenKind.STRING:
                self._set_cf(stream, Colour.STRING)
                self._set_bold(stream, False)
                stream.write(rtf_escape(text))
                after_dot = after_call_kw = after_import = False
                continue

            if kind is TokenKind.IDENT:
                upper = text.upper()

                if is_keyword(text):
                    self._set_cf(stream, Colour.KEYWORD)
                    self._set_bold(stream, True)
                    stream.write(rtf_escape(text))
                    self._set_bold(stream, False)
                    after_call_kw = upper == "CALL"
                    after_import = upper == "IMPORT"
                    after_dot = False
                elif after_import:
                    self._set_cf(stream, Colour.BLACK)
                    self._set_bold(stream, False)
                    stream.write(rtf_escape(text))
                    after_dot = after_call_kw = after_import = False
                elif after_dot:
                    self._set_cf(stream, Colour.MEMBER)
                    self._set_bold(stream, False)
                    stream.write(rtf_escape(text))
                    after_dot = after_call_kw = after_import = False
                else:
                    next_index = self._next_non_ws[index]
                    next_token = (
                        self._tokens[next_index]
                        if next_index is not None
                        else None
                    )
                    looks_callable = (
                        after_call_kw
                        or text.casefold() in self._callables
                        or (
                            next_token is not None
                            and next_token.kind is TokenKind.OP
                            and next_token.text == "("
                        )
                    )
                    if looks_callable:
                        self._set_cf(stream, Colour.CALLABLE)
                        self._set_bold(stream, True)
                        stream.write(rtf_escape(text))
                        self._set_bold(stream, False)
                    else:
                        self._set_cf(stream, Colour.BLACK)
                        self._set_bold(stream, False)
                        stream.write(rtf_escape(text))
                    after_dot = after_call_kw = after_import = False
                continue

            if kind is TokenKind.NUMBER:
                # A number immediately after an operator dot is an index
                # (array.0).  A leading-decimal literal (.5) is one number
                # token and therefore never reaches this branch with after_dot.
                self._set_cf(
                    stream,
                    Colour.INDEX if after_dot else Colour.BLACK,
                )
                self._set_bold(stream, False)
                stream.write(rtf_escape(text))
                after_dot = after_call_kw = after_import = False
                continue

            if kind is TokenKind.OP and text == ".":
                self._set_cf(stream, Colour.BLACK)
                self._set_bold(stream, False)
                stream.write(rtf_escape(text))
                after_dot = True
                after_call_kw = False
                after_import = False
                continue

            # Operators, punctuation and anything unrecognised.
            self._set_cf(stream, Colour.BLACK)
            self._set_bold(stream, False)
            stream.write(rtf_escape(text))
            after_dot = after_call_kw = after_import = False

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
