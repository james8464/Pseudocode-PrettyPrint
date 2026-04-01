from typing import List, Optional

from core.tokeniser import Token, is_keyword

_RTF_HEADER = "{\\rtf1\\ansi\\deff0\n{\\fonttbl{\\f0 Menlo;}}{\\colortbl;\\red38\\green38\\blue38;\\red210\\green39\\blue35;\\red168\\green53\\blue150;\\red0\\green114\\blue163;\\red24\\green39\\blue204;\\red118\\green70\\blue171;\\red107\\green107\\blue107;}\\f0\\fs24\n"
_RTF_FOOTER = "}\n"

_CF = {"black": 1, "string": 2, "keyword": 3, "member": 4, "index": 5, "callable": 6, "comment": 7}


def rtf_escape(_s: str) -> str:
    """escape text for RTF, handle unicode"""
    _out = []
    for _ch in _s:
        _o = ord(_ch)
        if _ch in ["\\", "{", "}"]:
            _out.append("\\" + _ch)
        elif _ch == "\n":
            _out.append("\\line\n")
        elif 0x20 <= _o <= 0x7E:
            _out.append(_ch)
        else:
            # unicode escape: \uN? where ? is fallback
            _out.append(f"\\u{_o}?")
    return "".join(_out)


def build_rtf_header() -> str:
    return _RTF_HEADER


def build_rtf_footer() -> str:
    return _RTF_FOOTER


def render_rtf(_tokens: List[Token]) -> str:
    _out: List[str] = []
    _current_cf: Optional[int] = None
    _current_bold: bool = False

    def set_cf(_name: str):
        nonlocal _current_cf
        _cf_val = _CF[_name]
        if _current_cf != _cf_val:
            _out.append(f"\\cf{_cf_val} ")
            _current_cf = _cf_val

    def set_bold(_bold: bool):
        nonlocal _current_bold
        if _current_bold != _bold:
            _out.append("\\b " if _bold else "\\b0 ")
            _current_bold = _bold

    set_cf("black")
    set_bold(False)

    _prev_non_ws: Optional[Token] = None
    _after_dot = False
    _after_call_kw = False
    _after_import = False

    _next_non_ws = {}
    _prev_idx = -1
    for _idx, _tok in enumerate(_tokens):
        if _tok.kind != "ws":
            if _prev_idx >= 0:
                _next_non_ws[_prev_idx] = _idx
            _prev_idx = _idx

    for _i, _t in enumerate(_tokens):
        if _t.kind == "ws":
            set_cf("black")
            set_bold(False)
            _out.append(rtf_escape(_t.text))
            continue

        if _t.kind == "comment":
            set_cf("comment")
            set_bold(False)
            _out.append(rtf_escape(_t.text))
            _prev_non_ws = _t
            _after_dot = False
            _after_call_kw = False
            _after_import = False
            continue

        if _t.kind == "string" or _t.kind == "char":
            set_cf("string")
            set_bold(False)
            _out.append(rtf_escape(_t.text))
            _prev_non_ws = _t
            _after_dot = False
            _after_call_kw = False
            _after_import = False
            continue

        if _t.kind == "ident":
            if is_keyword(_t.text):
                set_cf("keyword")
                set_bold(True)
                _out.append(rtf_escape(_t.text))
                set_bold(False)
                _after_call_kw = (_t.text.upper() == "CALL")
                _after_import = (_t.text.upper() == "IMPORT")
                _after_dot = False
            else:
                # after IMPORT -> black, not bold
                if _after_import:
                    set_cf("black")
                    set_bold(False)
                    _out.append(rtf_escape(_t.text))
                    _after_import = False
                    _after_call_kw = False
                    _after_dot = False
                # member after dot -> blue
                elif _after_dot:
                    set_cf("member")
                    set_bold(False)
                    _out.append(rtf_escape(_t.text))
                    _after_dot = False
                    _after_call_kw = False
                else:
                    _nxt_idx = _next_non_ws.get(_i)
                    _nxt = _tokens[_nxt_idx] if _nxt_idx is not None else None
                    _looks_callable = (
                        _after_call_kw
                        or (_t.text[:1].isupper())
                        or (_nxt is not None and _nxt.text == "(")
                    )
                    if _looks_callable:
                        set_cf("callable")
                        set_bold(True)
                        _out.append(rtf_escape(_t.text))
                        set_bold(False)
                    else:
                        set_cf("black")
                        set_bold(False)
                        _out.append(rtf_escape(_t.text))
                    _after_call_kw = False
            _prev_non_ws = _t
            continue

        if _t.kind == "number":
            # dark blue for .0 / .1 style indices
            if _prev_non_ws is not None and _prev_non_ws.text == ".":
                set_cf("index")
            else:
                set_cf("black")
            set_bold(False)
            _out.append(rtf_escape(_t.text))
            _prev_non_ws = _t
            _after_dot = False
            _after_call_kw = False
            _after_import = False
            continue

        if _t.text == ".":
            set_cf("black")
            set_bold(False)
            _out.append(rtf_escape(_t.text))
            _prev_non_ws = _t
            _after_dot = True
            _after_call_kw = False
            _after_import = False
            continue

        # operators and everything else
        set_cf("black")
        set_bold(False)
        _out.append(rtf_escape(_t.text))
        _prev_non_ws = _t
        _after_dot = False
        _after_call_kw = False
        _after_import = False

    return "".join(_out)
