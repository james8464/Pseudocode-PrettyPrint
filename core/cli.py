"""Command-line interface for the pseudocode RTF renderer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from core import __version__
from core.file_io import (
    InputOutcome,
    choose_output_path,
    process_input,
    read_file,
    read_input,
    render_document,
    unique_file_path,
    write_document,
)
from core.rtf import write_rtf
from core.tokeniser import LexWarning, TokeniseError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pseudocode-prettyprint",
        description=(
            "Convert Cambridge-style pseudocode to RTF with syntax "
            "highlighting."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="input file (omit to read from stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output file (single run) or output directory",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="write the RTF document to stdout instead of a file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _reconfigure_stdin() -> None:
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        # StringIO and some test doubles do not support reconfigure().
        pass


def _resolve_output(args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    """Return ``(output_file, output_dir)`` for the parsed arguments."""
    if args.output is None:
        return None, Path.cwd() / "outputs"

    output = Path(args.output)
    if output.exists() and output.is_dir():
        return None, output
    # A non-existing path without a suffix is treated as a directory;
    # `foo/` and `foo` both become Path("foo").
    if output.suffix == "":
        return None, output
    return output, None


def _print_warnings(warnings: tuple[LexWarning, ...]) -> None:
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)


def _process_once(
    text: str,
    args: argparse.Namespace,
    counter: int,
) -> int:
    try:
        result = render_document(text)
    except TokeniseError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    _print_warnings(result.warnings)

    if args.stdout:
        write_rtf(result.tokens, sys.stdout)
        return 0

    output_file, output_dir = _resolve_output(args)
    try:
        if output_file is not None:
            destination = (
                output_file if args.force else unique_file_path(output_file)
            )
        else:
            destination = choose_output_path(
                output_dir or Path.cwd() / "outputs",
                counter=counter,
                force=args.force,
            )

        write_document(destination, result.tokens)
    except OSError as error:
        print(f"Error: could not write output: {error}", file=sys.stderr)
        return 1

    print(f"Wrote: {destination}")
    return 0


def _read_file_or_report(path: Path) -> str | None:
    try:
        return read_file(path)
    except UnicodeDecodeError:
        print(f"Error: {path} is not valid UTF-8", file=sys.stderr)
    except OSError as error:
        print(f"Error: could not read {path}: {error}", file=sys.stderr)
    return None


def _run_interactive(args: argparse.Namespace) -> int:
    print("Pseudocode formatter - interactive mode")
    print("=" * 40)
    print("Paste your pseudocode. Type END (or :end) on its own line to finish.")
    print("Type QUIT to exit.\n")

    counter = 0
    while True:
        result = read_input()

        if result.outcome in (InputOutcome.QUIT, InputOutcome.EOF):
            print("Exiting...")
            return 0
        if result.outcome is InputOutcome.EMPTY or result.text is None:
            continue

        counter += 1
        try:
            status = _process_once(result.text, args, counter)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130

        if status != 0:
            counter -= 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.stdout and args.output is not None:
        parser.error("--stdout and --output cannot be used together")

    _reconfigure_stdin()

    if args.input is not None:
        text = _read_file_or_report(args.input)
        if text is None:
            return 1
        if not text.strip():
            print(f"Error: {args.input} is empty", file=sys.stderr)
            return 1
        try:
            return _process_once(text, args, 1)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130

    if not sys.stdin.isatty():
        result = read_input()
        if result.outcome is InputOutcome.EMPTY or result.text is None:
            print("Error: no input was provided", file=sys.stderr)
            return 1
        if result.outcome is not InputOutcome.TEXT:
            return 1
        try:
            return _process_once(result.text, args, 1)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130

    if args.output is not None:
        parser.error("--output is not supported in interactive mode")
    if args.stdout:
        parser.error("--stdout is not supported in interactive mode")

    return _run_interactive(args)
