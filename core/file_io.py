import sys
from pathlib import Path
from typing import List, Optional

from core.rtf import render_rtf
from core.tokeniser import tokenise


_OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def read_input() -> Optional[str]:
    if not sys.stdin.isatty():
        _text = sys.stdin.read()
        return _text if _text.strip() else None

    print("Paste your pseudocode. Type END on its own line to finish.")
    print("Type QUIT to exit.\n")
    _lines: List[str] = []
    while True:
        try:
            _line = input()
        except (EOFError, KeyboardInterrupt):
            return None
        _line_stripped = _line.strip()
        if _line_stripped.upper() == "QUIT":
            return None
        if _line_stripped.upper() in {"END", ":END"}:
            break
        _lines.append(_line)
    return "\n".join(_lines) + "\n" if _lines else None


def process_input(_text: str, _counter: int) -> None:
    _result = tokenise(_text)
    for _warning in _result.warnings:
        print(f"Warning: {_warning}", file=sys.stderr)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _rtf = render_rtf(_result.tokens)
    _out_name = f"pretty_pseudocode_{_counter}.rtf" if _counter > 1 else "pretty_pseudocode.rtf"
    _out_path = _OUTPUT_DIR / _out_name
    with open(_out_path, "w", encoding="utf-8") as _f:
        _f.write(_rtf)

    print(f"Wrote: {_out_path}\n")
