"""Display-aware smoke tests for the desktop interface.

These are skipped automatically on machines or CI runners without a GUI, so
the rest of the suite still runs everywhere.
"""

import tempfile
import unittest
from pathlib import Path

try:
    import tkinter
except ImportError:  # pragma: no cover - depends on the Python build
    tkinter = None  # type: ignore[assignment]


def _display_available() -> bool:
    if tkinter is None:
        return False
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.destroy()
    except Exception:  # pragma: no cover - depends on the environment
        return False
    return True


DISPLAY_AVAILABLE = _display_available()


@unittest.skipUnless(DISPLAY_AVAILABLE, "Tk display is unavailable")
class GuiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        from pseudocode_prettyprint.gui import PseudocodeApp
        from pseudocode_prettyprint.settings import Settings

        assert tkinter is not None
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = PseudocodeApp(self.root, settings=Settings())

    def tearDown(self) -> None:
        self.root.destroy()

    def test_live_preview_renders_tokens(self) -> None:
        self.app.editor.insert("1.0", 'IF x THEN\n    PRINT "hi"\nENDIF\n')
        self.app._refresh_preview()
        self.assertTrue(self.app._tokens)
        preview = self.app.preview.get("1.0", "end-1c")
        self.assertIn("IF", preview)
        self.assertIn('"hi"', preview)

    def test_unterminated_string_is_reported(self) -> None:
        self.app.editor.insert("1.0", 'PRINT "oops\n')
        self.app._refresh_preview()
        self.assertTrue(self.app._preview_error)
        self.assertEqual(self.app._tokens, ())
        self.assertIn("Unterminated", self.app.preview.get("1.0", "end-1c"))

    def test_theme_switch_updates_preview_palette(self) -> None:
        self.app._set_theme("dark")
        keyword = self.app.preview.tag_cget("colour_keyword", "foreground")
        self.assertEqual(keyword, "#FF7AB2")
        self.app._set_theme("light")
        keyword = self.app.preview.tag_cget("colour_keyword", "foreground")
        self.assertEqual(keyword, "#A83596")

    def test_save_writes_a_valid_rtf_document(self) -> None:
        self.app.editor.insert("1.0", 'PRINT "hi"\n')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "output.rtf"
            self.assertTrue(self.app._write_to(target))
            document = target.read_text(encoding="ascii")
        self.assertTrue(document.startswith("{\\rtf1"))
        self.assertTrue(document.endswith("}\n"))

    def test_export_does_not_clear_the_dirty_flag(self) -> None:
        self.app.editor.insert("1.0", 'PRINT "hi"\n')
        self.app._refresh_preview()
        self.app._dirty = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "output.rtf"
            self.assertTrue(self.app._write_to(target))
        self.assertTrue(self.app._dirty)

    def test_save_source_round_trips_utf8(self) -> None:
        source = "x ← 1\nPRINT \"héllo\"\n"
        self.app.editor.insert("1.0", source)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "code.txt"
            self.assertTrue(self.app._write_source_to(target))
            self.assertEqual(target.read_text(encoding="utf-8"), source)
            self.assertEqual(self.app._source_path, target)
        self.assertFalse(self.app._dirty)

    def test_font_size_is_clamped(self) -> None:
        self.app._set_font_size(500)
        self.assertEqual(self.app.settings.font_size, 32)
        self.app._set_font_size(1)
        self.assertEqual(self.app.settings.font_size, 9)

    def test_empty_editor_refuses_export(self) -> None:
        from unittest.mock import patch

        self.app.editor.delete("1.0", "end")
        self.app._refresh_preview()
        with patch("pseudocode_prettyprint.gui.messagebox.showinfo") as info:
            self.assertFalse(self.app._prepare_export())
        info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
