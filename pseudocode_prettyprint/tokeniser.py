"""Lexer for Cambridge-style pseudocode.

The lexer deliberately keeps malformed input visible rather than silently
swallowing it: an unterminated double-quoted string is a hard error, and
unrecognised characters produce warnings with line/column positions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from pseudocode_prettyprint.constants import KEYWORDS


class TokenKind(str, Enum):
    COMMENT = "comment"
    STRING = "string"
    NUMBER = "number"
    IDENT = "ident"
    OP = "op"
    WS = "ws"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    text: str


@dataclass(frozen=True, slots=True)
class LexWarning:
    message: str
    line: int
    column: int

    def __str__(self) -> str:
        if self.line > 0:
            return f"{self.message} (line {self.line}, column {self.column})"
        return self.message


class TokeniseError(ValueError):
    """Raised when the input cannot be tokenised safely."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} (line {line}, column {column})")
        self.line = line
        self.column = column


@dataclass(frozen=True, slots=True)
class TokeniseResult:
    tokens: tuple[Token, ...]
    warnings: tuple[LexWarning, ...]


# Tokenisation order matters: comments and strings must be consumed whole
# before operators can see their punctuation.  Double-quoted strings may not
# cross a line boundary; allowing that makes a single missing quote silently
# swallow the rest of the file.
TOKEN_RE = re.compile(
    r"""
      (?P<comment>//[^\n]*)
    | (?P<string>“[^”\n]*”|"(?:[^"\\\n]|\\.)*")
    | (?P<number>\d+\.\d*|(?<![\w.)\]])\.\d+|\d+)
    | (?P<ident>[A-Za-z][A-Za-z0-9_]*\b)
    | (?P<op><>|>=|<=|=|<|>|\+|-|\*|/|\(|\)|\[|\]|\{|\}|,|:|\.|&|←)
    | (?P<ws>\s+)
    | (?P<other>.)
    """,
    re.VERBOSE | re.ASCII,
)

_KIND_BY_NAME = {kind.value: kind for kind in TokenKind}
_DEFAULT_MAX_WARNINGS = 100


def _line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_newline = text.rfind("\n", 0, offset)
    return line, offset - last_newline


def tokenise(text: str, *, max_warnings: int = _DEFAULT_MAX_WARNINGS) -> TokeniseResult:
    """Tokenise *text* and return tokens plus non-fatal diagnostics.

    Raises:
        TokeniseError: if a double-quoted string is not terminated on its line.
    """

    # Normalise line endings so that a lone CR cannot reach the RTF escaper.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    tokens: list[Token] = []
    warnings: list[LexWarning] = []
    suppressed = 0
    limit = max(0, max_warnings)

    for match in TOKEN_RE.finditer(text):
        group = match.lastgroup
        assert group is not None  # every alternative is a named group
        kind = _KIND_BY_NAME[group]
        value = match.group()

        if kind is TokenKind.OTHER:
            line, column = _line_col(text, match.start())
            if value in {'"', "“"}:
                raise TokeniseError("Unterminated string literal", line, column)
            if len(warnings) < limit:
                warnings.append(
                    LexWarning(
                        f"Unrecognised character {value!r}; rendered as plain text",
                        line,
                        column,
                    )
                )
            else:
                suppressed += 1

        tokens.append(Token(kind=kind, text=value))

    if suppressed:
        warnings.append(
            LexWarning(f"{suppressed} additional warning(s) suppressed", 0, 0)
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"Suppressed {suppressed} warning(s) (limit: {max_warnings})")

    return TokeniseResult(tokens=tuple(tokens), warnings=tuple(warnings))


def is_keyword(identifier: str) -> bool:
    """Return whether *identifier* is a reserved word or built-in."""
    return identifier.upper() in KEYWORDS
