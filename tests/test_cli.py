"""Tests for the command-line interface."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from pseudocode_prettyprint.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(argv)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_input_file_to_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text('PRINT "hi"\n', encoding="utf-8")
            output = Path(directory) / "report.rtf"

            status, stdout, _ = self.run_cli([str(source), "-o", str(output)])

            self.assertEqual(status, 0)
            self.assertTrue(output.exists())
            self.assertIn(f"Wrote: {output}", stdout)

    def test_stdout_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("x ← 1\n", encoding="utf-8")

            status, stdout, _ = self.run_cli([str(source), "--stdout"])

            self.assertEqual(status, 0)
            self.assertTrue(stdout.startswith("{\\rtf1"))
            self.assertTrue(stdout.endswith("}\n"))

    def test_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("x ← 1\n", encoding="utf-8")
            output_dir = Path(directory) / "out"

            status, _, _ = self.run_cli([str(source), "-o", str(output_dir)])

            self.assertEqual(status, 0)
            self.assertTrue((output_dir / "pretty_pseudocode.rtf").exists())

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("x ← 1\n", encoding="utf-8")
            output = Path(directory) / "report.rtf"
            output.write_text("old", encoding="utf-8")

            status, _, _ = self.run_cli([str(source), "-o", str(output)])

            self.assertEqual(status, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "old")
            self.assertTrue((Path(directory) / "report_2.rtf").exists())

    def test_existing_suffixless_output_is_treated_as_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("x ← 1\n", encoding="utf-8")
            output = Path(directory) / "report"
            output.write_text("old", encoding="utf-8")

            status, _, _ = self.run_cli([str(source), "-o", str(output)])

            self.assertEqual(status, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "old")
            self.assertTrue((Path(directory) / "report_2").exists())

    def test_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("x ← 1\n", encoding="utf-8")
            output = Path(directory) / "report.rtf"
            output.write_text("old", encoding="utf-8")

            status, _, _ = self.run_cli(
                [str(source), "-o", str(output), "--force"]
            )

            self.assertEqual(status, 0)
            self.assertNotEqual(output.read_text(encoding="utf-8"), "old")

    def test_empty_file_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("   \n", encoding="utf-8")

            status, _, stderr = self.run_cli([str(source)])

            self.assertEqual(status, 1)
            self.assertIn("empty", stderr)

    def test_missing_file_returns_failure(self) -> None:
        status, _, stderr = self.run_cli(["/definitely/not/here.txt"])
        self.assertEqual(status, 1)
        self.assertIn("could not read", stderr)

    def test_conflicting_output_flags(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text("x ← 1\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as context:
                self.run_cli(
                    [str(source), "--stdout", "-o", str(Path(directory) / "a.rtf")]
                )
        self.assertEqual(context.exception.code, 2)

    def test_gui_conflicts_with_output_flags(self) -> None:
        with self.assertRaises(SystemExit) as context:
            self.run_cli(["--gui", "-o", "report.rtf"])
        self.assertEqual(context.exception.code, 2)

    def test_unterminated_string_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_text('PRINT "oops\n', encoding="utf-8")
            status, _, stderr = self.run_cli([str(source)])
        self.assertEqual(status, 1)
        self.assertIn("Unterminated string", stderr)


if __name__ == "__main__":
    unittest.main()
