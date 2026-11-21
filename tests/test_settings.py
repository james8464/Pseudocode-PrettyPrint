"""Tests for persistent desktop settings."""

import json
import tempfile
import unittest
from pathlib import Path

from pseudocode_prettyprint.settings import (
    Settings,
    load_settings,
    save_settings,
    settings_path,
)


class SettingsTests(unittest.TestCase):
    def test_missing_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            self.assertEqual(load_settings(path), Settings())

    def test_round_trip(self) -> None:
        settings = Settings(
            theme="dark",
            font_size=18,
            wrap=False,
            geometry="1000x700+20+30",
            last_directory="/tmp",
            recent_files=["/tmp/a.txt"],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "settings.json"
            save_settings(settings, path)
            self.assertTrue(path.exists())
            self.assertEqual(load_settings(path), settings)

    def test_corrupt_json_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_settings(path), Settings())

    def test_invalid_values_are_coerced(self) -> None:
        raw = {
            "theme": "purple",
            "font_size": 500,
            "wrap": "yes",
            "geometry": 3,
            "recent_files": [1, "/tmp/a.txt", "/tmp/a.txt"],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            settings = load_settings(path)
        self.assertEqual(settings.theme, "light")
        self.assertEqual(settings.font_size, 32)
        self.assertTrue(settings.wrap)
        self.assertEqual(settings.geometry, "")
        self.assertEqual(settings.recent_files, ["/tmp/a.txt"])

    def test_font_size_is_clamped_at_the_bottom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"font_size": 1}', encoding="utf-8")
            self.assertEqual(load_settings(path).font_size, 9)

    def test_remember_file_moves_entry_to_the_front(self) -> None:
        settings = Settings(recent_files=["/tmp/a.txt", "/tmp/b.txt"])
        settings.remember_file(Path("/tmp/b.txt"))
        a = str(Path("/tmp/a.txt").resolve())
        b = str(Path("/tmp/b.txt").resolve())
        self.assertEqual(settings.recent_files, [b, a])

    def test_remember_file_sets_last_directory(self) -> None:
        settings = Settings()
        settings.remember_file(Path("/tmp/example/code.txt"))
        expected = str(Path("/tmp/example/code.txt").resolve().parent)
        self.assertEqual(settings.last_directory, expected)

    def test_recent_files_are_capped(self) -> None:
        settings = Settings()
        for number in range(20):
            settings.remember_file(Path(f"/tmp/file{number}.txt"))
        newest = str(Path("/tmp/file19.txt").resolve())
        self.assertEqual(len(settings.recent_files), 8)
        self.assertEqual(settings.recent_files[0], newest)

    def test_settings_path_uses_app_directory(self) -> None:
        self.assertEqual(settings_path().parent.name, "PseudocodePrettyPrint")


if __name__ == "__main__":
    unittest.main()
