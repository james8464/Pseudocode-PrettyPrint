"""Regression tests for RTF rendering and escaping."""

import re
import unittest

from core.constants import COLOURS
from core.rtf import _CF, build_rtf_header, render_rtf, rtf_escape
from core.tokeniser import tokenise


def render(source: str) -> str:
    return render_rtf(tokenise(source).tokens)


class EscapeTests(unittest.TestCase):
    def test_backslash_and_braces(self) -> None:
        self.assertEqual(rtf_escape("\\{}"), "\\\\\\{\\}")

    def test_newline_is_line_break(self) -> None:
        self.assertEqual(rtf_escape("a\nb"), "a\\line\nb")

    def test_tab_is_tab_stop(self) -> None:
        self.assertEqual(rtf_escape("\t"), "\\tab ")

    def test_bmp_unicode(self) -> None:
        self.assertEqual(rtf_escape("é"), "\\u233?")

    def test_astral_unicode_uses_surrogate_pair(self) -> None:
        self.assertEqual(rtf_escape("😀"), "\\u-10179?\\u-8704?")

    def test_unknown_control_character_is_dropped(self) -> None:
        self.assertEqual(rtf_escape("\x01"), "")

    def test_printable_ascii_is_untouched(self) -> None:
        self.assertEqual(rtf_escape("abc 123"), "abc 123")


class HeaderTests(unittest.TestCase):
    def test_header_uses_palette_values(self) -> None:
        header = build_rtf_header()
        values = re.findall(r"\\red(\d+)\\green(\d+)\\blue(\d+)", header)
        expected = [tuple(str(channel) for channel in rgb) for rgb in COLOURS.values()]
        self.assertEqual(values, expected)

    def test_cf_mapping_matches_palette_order(self) -> None:
        self.assertEqual(
            _CF,
            {colour: index + 1 for index, colour in enumerate(COLOURS)},
        )

    def test_paste_safety_directives(self) -> None:
        header = build_rtf_header()
        self.assertIn("\\uc1", header)
        self.assertIn("\\plain", header)
        self.assertIn("\\fmodern", header)
        self.assertIn("\\fcharset0", header)


class RenderingTests(unittest.TestCase):
    def test_uppercase_variables_are_not_callable(self) -> None:
        output = render("Result ← Total + 1")
        self.assertNotIn("\\cf6", output)

    def test_declared_procedure_is_callable(self) -> None:
        output = render("PROCEDURE Foo()\nENDPROCEDURE\nFoo\n")
        self.assertGreaterEqual(output.count("\\cf6"), 2)

    def test_call_keyword_makes_next_identifier_callable(self) -> None:
        output = render("CALL doThing")
        self.assertIn("\\cf6 \\b doThing", output)

    def test_function_call_by_parenthesis(self) -> None:
        output = render("x ← myFunc(3)")
        self.assertIn("\\cf6 \\b myFunc", output)

    def test_member_after_dot(self) -> None:
        output = render("obj.field")
        self.assertIn("\\cf4 field", output)

    def test_dot_does_not_leak_across_whitespace(self) -> None:
        output = render("obj.\nname")
        self.assertNotIn("\\cf4 name", output)

    def test_leading_decimal_is_not_an_index(self) -> None:
        output = render("x ← .5")
        self.assertNotIn("\\cf5", output)

    def test_dot_index_is_coloured(self) -> None:
        output = render("arr.0")
        self.assertIn("\\cf5 0", output)

    def test_end_is_plain_text(self) -> None:
        output = render("end ← 1")
        self.assertNotIn("\\cf3", output)
        self.assertNotIn("\\cf6", output)

    def test_comment_is_grey(self) -> None:
        output = render("// comment")
        self.assertIn("\\cf7", output)

    def test_string_is_red(self) -> None:
        output = render('PRINT "hi"')
        self.assertIn('\\cf2 "hi"', output)

    def test_keyword_is_bold(self) -> None:
        output = render("IF x THEN")
        self.assertIn("\\cf3 \\b IF\\b0", output)


if __name__ == "__main__":
    unittest.main()
