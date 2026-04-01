import re
from dataclasses import dataclass
from typing import List

from core.constants import KEYWORDS


@dataclass
class Token:
    kind: str
    text: str


# tokenisation - order matters (strings before comments)
TOKEN_RE = re.compile(
    r"""
    (?P<comment>//[^\n]*)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<char>'(?:[^'\\]|\\.)*')
  | (?P<arrow>←)
  | (?P<number>\b\d+(?:\.\d+)?\b)
  | (?P<ident>\b[A-Za-z][A-Za-z0-9_]*\b)
  | (?P<op><>|>=|<=|=|<|>|\+|-|\*|/|\(|\)|\[|\]|\{|\}|,|:|\.|&)
  | (?P<ws>\s+)
  | (?P<other>.)
    """,
    re.VERBOSE,
)


def tokenise(_text: str) -> List[Token]:
    _tokens: List[Token] = []
    for _m in TOKEN_RE.finditer(_text):
        _kind = _m.lastgroup or "other"
        _tokens.append(Token(kind=_kind, text=_m.group()))
    return _tokens


def is_keyword(_ident: str) -> bool:
    return _ident.upper() in KEYWORDS
