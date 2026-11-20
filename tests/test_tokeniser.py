"""Regression tests for the lexer."""

import unittest

from pseudocode_prettyprint.tokeniser import (
    TokeniseError,
    TokenKind,
    is_keyword,
    tokenise,
)


class TokeniserTests(unittest.TestCase):
    def token_kinds(self, source: str) -> list[TokenKind]:
        return [token.kind for token in tokenise(source).tokens]

    def test_unterminated_string_raises(self) -> None:
        with self.assertRaises(TokeniseError) as context:
            tokenise('PRINT "hello\nDECLARE x : INTEGER\n')
        self.assertEqual(context.exception.line, 1)
        self.assertEqual(context.exception.column, 7)

    def test_strings_are_independent_per_line(self) -> None:
        result = tokenise('PRINT "hello"\nPRINT "world"\n')
        string_tokens = [
            token for token in result.tokens if token.kind is TokenKind.STRING
        ]
        self.assertEqual(
            [token.text for token in string_tokens],
            ['"hello"', '"world"'],
        )

    def test_curly_quotes_are_strings(self) -> None:
        result = tokenise("PRINT “hello”\n")
        strings = [token for token in result.tokens if token.kind is TokenKind.STRING]
        self.assertEqual([token.text for token in strings], ["“hello”"])
        self.assertEqual(result.warnings, ())

    def test_apostrophes_are_not_character_literals(self) -> None:
        result = tokenise("it's Bob's book")
        kinds = [token.kind for token in result.tokens]
        self.assertNotIn(TokenKind.STRING, kinds)
        self.assertIn(TokenKind.OTHER, kinds)
        self.assertEqual(
            [token.text for token in result.tokens if token.kind is TokenKind.OTHER],
            ["'", "'"],
        )

    def test_leading_decimal_is_one_number(self) -> None:
        result = tokenise("x ← .5")
        numbers = [
            token.text
            for token in result.tokens
            if token.kind is TokenKind.NUMBER
        ]
        self.assertEqual(numbers, [".5"])

    def test_dot_index_remains_separate(self) -> None:
        result = tokenise("arr.0")
        kinds = [token.kind for token in result.tokens]
        self.assertEqual(
            kinds,
            [TokenKind.IDENT, TokenKind.OP, TokenKind.NUMBER],
        )

    def test_crlf_and_cr_are_normalised(self) -> None:
        result = tokenise("a\r\nb\rc")
        self.assertNotIn("\r", "".join(token.text for token in result.tokens))

    def test_tab_is_whitespace(self) -> None:
        result = tokenise("\tPRINT")
        self.assertEqual(result.tokens[0].kind, TokenKind.WS)
        self.assertEqual(result.tokens[0].text, "\t")

    def test_comment_consumes_rest_of_line(self) -> None:
        result = tokenise("// comment with \"quote\nPRINT")
        self.assertEqual(result.tokens[0].kind, TokenKind.COMMENT)
        self.assertEqual(result.tokens[0].text, '// comment with "quote')

    def test_keywords_are_case_insensitive(self) -> None:
        self.assertTrue(is_keyword("if"))
        self.assertTrue(is_keyword("IF"))

    def test_end_is_not_a_keyword(self) -> None:
        self.assertFalse(is_keyword("END"))

    def test_unrecognised_characters_warn(self) -> None:
        result = tokenise("x ? y")
        self.assertTrue(
            any("Unrecognised character" in str(w) for w in result.warnings)
        )

    def test_warning_count_is_capped(self) -> None:
        result = tokenise("?" * 150)
        self.assertLessEqual(len(result.warnings), 101)
        self.assertIn("suppressed", str(result.warnings[-1]))

    def test_alphanumeric_run_does_not_become_other_tokens(self) -> None:
        result = tokenise("123abc")
        self.assertEqual(
            [token.kind for token in result.tokens],
            [TokenKind.NUMBER, TokenKind.IDENT],
        )


if __name__ == "__main__":
    unittest.main()
