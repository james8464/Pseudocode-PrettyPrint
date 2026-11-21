"""Input, output and file-handling helpers."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pseudocode_prettyprint.rtf import write_rtf
from pseudocode_prettyprint.tokeniser import LexWarning, Token, tokenise


class InputOutcome(str, Enum):
    """The result of attempting to read one input block."""

    TEXT = "text"
    EMPTY = "empty"
    QUIT = "quit"
    EOF = "eof"


@dataclass(frozen=True, slots=True)
class InputResult:
    """One input block, or the reason no block was produced."""

    outcome: InputOutcome
    text: str | None = None


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Tokens and diagnostics produced from one input block."""

    tokens: tuple[Token, ...]
    warnings: tuple[LexWarning, ...]


def read_input(*, interactive: bool | None = None) -> InputResult:
    """Read one block from stdin.

    Piped input is read to EOF.  On a terminal, lines are read until a
    sentinel line (``END`` or ``:end``) or ``QUIT``; Ctrl-D is EOF and
    Ctrl-C is treated as a quit request.  ``interactive`` overrides the
    automatic ``isatty()`` check when the caller has already decided.
    """

    if interactive is None:
        interactive = sys.stdin.isatty()

    if not interactive:
        text = sys.stdin.read()
        if not text.strip():
            return InputResult(InputOutcome.EMPTY)
        return InputResult(InputOutcome.TEXT, text)

    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            return InputResult(InputOutcome.EOF)
        except KeyboardInterrupt:
            return InputResult(InputOutcome.QUIT)

        stripped = line.strip()
        if stripped.upper() == "QUIT":
            return InputResult(InputOutcome.QUIT)
        if stripped.upper() in {"END", ":END"}:
            break
        lines.append(line)

    if not lines:
        return InputResult(InputOutcome.EMPTY)
    return InputResult(InputOutcome.TEXT, "\n".join(lines) + "\n")


def read_file(path: Path) -> str:
    """Read a UTF-8 input file."""
    return path.read_text(encoding="utf-8")


def render_document(text: str) -> RenderResult:
    """Tokenise *text* and return its tokens and diagnostics."""
    result = tokenise(text)
    return RenderResult(tokens=result.tokens, warnings=result.warnings)


def _output_name(counter: int) -> str:
    if counter <= 1:
        return "pretty_pseudocode.rtf"
    return f"pretty_pseudocode_{counter}.rtf"


def choose_output_path(
    output_dir: Path,
    *,
    counter: int = 1,
    force: bool = False,
) -> Path:
    """Choose a non-existing output path, creating the directory if needed."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if force:
        return output_dir / _output_name(counter)

    number = max(1, counter)
    while True:
        candidate = output_dir / _output_name(number)
        if not candidate.exists():
            return candidate
        number += 1


def unique_file_path(path: Path) -> Path:
    """Return *path*, or a numbered sibling if it already exists."""
    path = Path(path)
    if not path.exists():
        return path

    for number in range(2, 10_000):
        candidate = path.with_name(f"{path.stem}_{number}{path.suffix}")
        # Use atomic check-and-act to avoid race conditions
        try:
            candidate.touch(exist_ok=False)
            return candidate
        except FileExistsError:
            # File was created by another process, try next number
            continue
    raise FileExistsError(f"Could not find a free output name near {path}")


def write_document(path: Path, tokens: tuple[Token, ...]) -> None:
    """Atomically write an RTF document to *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            # rtf_escape() converts every non-ASCII character to \uN, so the
            # document is ASCII by construction; enforce that invariant.
            encoding="ascii",
            newline="",
        ) as stream:
            write_rtf(tokens, stream)
            stream.flush()
            os.fsync(stream.fileno())

        # mkstemp creates files with 0600 permissions; give the final
        # document normal user-readable permissions.
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temporary_path.unlink()
        raise


def write_source(path: Path, text: str) -> None:
    """Atomically write UTF-8 pseudocode source to *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())

        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temporary_path.unlink()
        raise


def process_input(
    text: str,
    *,
    output_dir: Path | None = None,
    output_file: Path | None = None,
    counter: int = 1,
    force: bool = False,
) -> tuple[Path, RenderResult]:
    """Render *text* and write it to a file, returning the path and result."""

    result = render_document(text)

    if output_file is not None:
        destination = Path(output_file)
        if destination.is_dir():
            destination = choose_output_path(
                destination,
                counter=counter,
                force=force,
            )
        elif not force:
            destination = unique_file_path(destination)
    else:
        destination = choose_output_path(
            output_dir or Path.cwd() / "outputs",
            counter=counter,
            force=force,
        )

    write_document(destination, result.tokens)
    return destination, result
