"""Tests for the shared highlighting rules."""

import unittest

from pseudocode_prettyprint.constants import Colour
from pseudocode_prettyprint.highlight import HighlightedToken, highlight_tokens
from pseudocode_prettyprint.tokeniser import TokenKind, tokenise


def highlight(source: str) -> tuple[HighlightedToken, ...]:
    return highlight_tokens(tokenise(source).tokens)


def find(source: str, text: str) -> HighlightedToken:
    for item in highlight(source):
        if item.text == text:
            return item
    raise AssertionError(f"{text!r} is not a token in {source!r}")


class HighlightTests(unittest.TestCase):
    def test_keyword_is_bold(self) -> None:
        item = find("IF x THEN", "IF")
        self.assertEqual(item.colour, Colour.KEYWORD)
        self.assertTrue(item.bold)

    def test_whitespace_inherits_colour(self) -> None:
        item = find("x ← 1", " ")
        self.assertIsNone(item.colour)
        self.assertFalse(item.bold)

    def test_declared_procedure_is_callable(self) -> None:
        item = find("PROCEDURE Foo()\nENDPROCEDURE\n", "Foo")
        self.assertEqual(item.colour, Colour.CALLABLE)
        self.assertTrue(item.bold)

    def test_call_argument_is_callable_across_space(self) -> None:
        item = find("CALL doThing\n", "doThing")
        self.assertEqual(item.colour, Colour.CALLABLE)

    def test_call_argument_does_not_cross_line_break(self) -> None:
        item = find("CALL\ndoThing\n", "doThing")
        self.assertEqual(item.colour, Colour.BLACK)

    def test_import_name_is_plain(self) -> None:
        item = find("IMPORT Maths\n", "Maths")
        self.assertEqual(item.colour, Colour.BLACK)
        self.assertFalse(item.bold)

    def test_member_after_dot(self) -> None:
        item = find("obj.field\n", "field")
        self.assertEqual(item.colour, Colour.MEMBER)

    def test_index_after_dot(self) -> None:
        item = find("arr.0\n", "0")
        self.assertEqual(item.colour, Colour.INDEX)

    def test_leading_decimal_is_plain(self) -> None:
        item = find("x ← .5\n", ".5")
        self.assertEqual(item.colour, Colour.BLACK)

    def test_uppercase_variable_is_not_callable(self) -> None:
        item = find("Result\n", "Result")
        self.assertEqual(item.colour, Colour.BLACK)

    def test_parenthesised_name_is_callable(self) -> None:
        item = find("x ← myFunc(3)\n", "myFunc")
        self.assertEqual(item.colour, Colour.CALLABLE)

    def test_string_and_comment_colours(self) -> None:
        string = find('PRINT "hi"\n', '"hi"')
        comment = find("// note\n", "// note")
        self.assertEqual(string.colour, Colour.STRING)
        self.assertEqual(comment.colour, Colour.COMMENT)

    def test_every_token_is_preserved(self) -> None:
        tokens = tokenise('PRINT "hi"\n')
        highlighted = highlight_tokens(tokens.tokens)
        self.assertEqual(
            [item.text for item in highlighted],
            [token.text for token in tokens.tokens],
        )

    def test_kind_and_text_properties(self) -> None:
        item = find("x ← 1\n", "x")
        self.assertEqual(item.kind, TokenKind.IDENT)
        self.assertEqual(item.text, "x")


if __name__ == "__main__":
    unittest.main()
