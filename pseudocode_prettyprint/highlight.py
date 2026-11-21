"""Shared syntax-highlighting rules for the RTF and desktop renderers.

Keeping the classification in one place means the GUI preview and the
exported RTF document always agree about which token gets which style.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pseudocode_prettyprint.constants import Colour
from pseudocode_prettyprint.tokeniser import Token, TokenKind, is_keyword

# Identifiers introduced by these keywords are callable/type names.  This is
# a small declaration-aware symbol table, not a capitalisation heuristic.
_DECLARATION_KEYWORDS = frozenset({
    "PROCEDURE",
    "FUNCTION",
    "TYPE",
    "CLASS",
    "NEW",
    "INHERITS",
})


@dataclass(frozen=True, slots=True)
class HighlightedToken:
    """One token together with the style it should be rendered in."""

    token: Token
    colour: Colour | None
    bold: bool

    @property
    def text(self) -> str:
        """The original token text."""
        return self.token.text

    @property
    def kind(self) -> TokenKind:
        """The token kind."""
        return self.token.kind


def _next_non_ws_indices(tokens: Sequence[Token]) -> list[int | None]:
    """For each token, the index of the next non-whitespace token (or None)."""
    next_indices: list[int | None] = [None] * len(tokens)
    next_index: int | None = None
    for index in range(len(tokens) - 1, -1, -1):
        next_indices[index] = next_index
        if tokens[index].kind is not TokenKind.WS:
            next_index = index
    return next_indices


def _find_callables(
    tokens: Sequence[Token],
    next_non_ws: Sequence[int | None],
) -> frozenset[str]:
    """Collect case-folded names introduced by declaration keywords."""
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


def highlight_tokens(tokens: Sequence[Token]) -> tuple[HighlightedToken, ...]:
    """Classify every token for syntax highlighting.

    Whitespace keeps ``colour=None`` so a renderer can let it inherit the
    surrounding colour (RTF) or use its own default (GUI).
    """

    next_non_ws = _next_non_ws_indices(tokens)
    callables = _find_callables(tokens, next_non_ws)

    after_dot = False
    after_call_kw = False
    after_import = False
    highlighted: list[HighlightedToken] = []

    for index, token in enumerate(tokens):
        kind = token.kind
        text = token.text
        colour: Colour | None
        bold = False

        if kind is TokenKind.WS:
            # A dot cannot continue a member chain across whitespace, and
            # CALL/IMPORT do not continue across a line break.
            after_dot = False
            if "\n" in text:
                after_call_kw = False
                after_import = False
            highlighted.append(HighlightedToken(token, None, False))
            continue

        if kind is TokenKind.COMMENT:
            colour = Colour.COMMENT
            after_dot = after_call_kw = after_import = False
        elif kind is TokenKind.STRING:
            colour = Colour.STRING
            after_dot = after_call_kw = after_import = False
        elif kind is TokenKind.IDENT:
            upper = text.upper()
            if is_keyword(text):
                colour = Colour.KEYWORD
                bold = True
                after_call_kw = upper == "CALL"
                after_import = upper == "IMPORT"
                after_dot = False
            elif after_import:
                colour = Colour.BLACK
                after_dot = after_call_kw = after_import = False
            elif after_dot:
                colour = Colour.MEMBER
                after_dot = after_call_kw = after_import = False
            else:
                next_index = next_non_ws[index]
                next_token = (
                    tokens[next_index] if next_index is not None else None
                )
                looks_callable = (
                    after_call_kw
                    or text.casefold() in callables
                    or (
                        next_token is not None
                        and next_token.kind is TokenKind.OP
                        and next_token.text == "("
                    )
                )
                colour = Colour.CALLABLE if looks_callable else Colour.BLACK
                bold = looks_callable
                after_dot = after_call_kw = after_import = False
        elif kind is TokenKind.NUMBER:
            # A number immediately after an operator dot is an index
            # (array.0).  A leading-decimal literal (.5) is one number token
            # and therefore never reaches this branch with after_dot set.
            colour = Colour.INDEX if after_dot else Colour.BLACK
            after_dot = after_call_kw = after_import = False
        elif kind is TokenKind.OP and text == ".":
            colour = Colour.BLACK
            after_dot = True
            after_call_kw = False
            after_import = False
        else:
            # Operators, punctuation and anything unrecognised.
            colour = Colour.BLACK
            after_dot = after_call_kw = after_import = False

        highlighted.append(HighlightedToken(token, colour, bold))

    return tuple(highlighted)
