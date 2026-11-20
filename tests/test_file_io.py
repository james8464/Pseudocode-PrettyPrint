"""Tests for input handling and atomic output writing."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.file_io import (
    InputOutcome,
    choose_output_path,
    process_input,
    read_file,
    read_input,
    unique_file_path,
)


class ReadInputTests(unittest.TestCase):
    def test_piped_text(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("PRINT 1\n")):
            result = read_input()
        self.assertEqual(result.outcome, InputOutcome.TEXT)
        self.assertEqual(result.text, "PRINT 1\n")

    def test_whitespace_only_is_empty(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("   \n\n")):
            result = read_input()
        self.assertEqual(result.outcome, InputOutcome.EMPTY)
        self.assertIsNone(result.text)

    def test_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("x ← 1\n", encoding="utf-8")
            self.assertEqual(read_file(path), "x ← 1\n")


class OutputPathTests(unittest.TestCase):
    def test_directory_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "nested" / "outputs"
            path = choose_output_path(output_dir)
            self.assertTrue(output_dir.is_dir())
            self.assertEqual(path.name, "pretty_pseudocode.rtf")

    def test_existing_names_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            first = choose_output_path(output_dir)
            first.write_text("one", encoding="utf-8")
            second = choose_output_path(output_dir)
            self.assertEqual(second.name, "pretty_pseudocode_2.rtf")

    def test_unique_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.rtf"
            path.write_text("one", encoding="utf-8")
            self.assertEqual(unique_file_path(path).name, "out_2.rtf")


class ProcessInputTests(unittest.TestCase):
    def test_writes_rtf_and_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "outputs"
            path, result = process_input('PRINT "hi"\n', output_dir=output_dir)
            self.assertTrue(path.exists())
            self.assertEqual(result.warnings, ())
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("{\\rtf1"))
            self.assertTrue(text.endswith("}\n"))

    def test_second_run_gets_numbered_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            first, _ = process_input("x ← 1\n", output_dir=output_dir)
            second, _ = process_input("x ← 2\n", output_dir=output_dir)
            self.assertEqual(first.name, "pretty_pseudocode.rtf")
            self.assertEqual(second.name, "pretty_pseudocode_2.rtf")

    def test_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            path, _ = process_input("x ← 1\n", output_dir=output_dir)
            original = path.read_text(encoding="utf-8")
            process_input('PRINT "different"\n', output_dir=output_dir, force=True)
            self.assertNotEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(
                sorted(p.name for p in output_dir.iterdir()),
                ["pretty_pseudocode.rtf"],
            )

    def test_explicit_output_file_is_unique(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.rtf"
            first, _ = process_input("x ← 1\n", output_file=output)
            second, _ = process_input("x ← 2\n", output_file=output)
            self.assertEqual(first.name, "report.rtf")
            self.assertEqual(second.name, "report_2.rtf")


if __name__ == "__main__":
    unittest.main()
