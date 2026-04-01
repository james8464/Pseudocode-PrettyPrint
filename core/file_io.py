import sys
from pathlib import Path
from typing import List, Optional

from core.rtf import build_rtf_header, build_rtf_footer, render_rtf
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
        if _line_stripped == "QUIT":
            return None
        if _line_stripped == "END":
            break
        _lines.append(_line)
    return "\n".join(_lines) + "\n" if _lines else None


def process_input(_text: str, _counter: int) -> None:
    _tokens = tokenise(_text)

    _rtf = build_rtf_header() + render_rtf(_tokens) + build_rtf_footer()
    _out_name = f"pretty_pseudocode_{_counter}.rtf" if _counter > 1 else "pretty_pseudocode.rtf"
    _out_path = _OUTPUT_DIR / _out_name
    with open(_out_path, "w", encoding="utf-8") as _f:
        _f.write(_rtf)

    print(f"Wrote: {_out_path}\n")
