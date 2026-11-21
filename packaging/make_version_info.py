"""Generate a PyInstaller version resource for the Windows executable."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pseudocode_prettyprint import __version__  # noqa: E402


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".") if part.isdigit()]
    parts = (parts + [0, 0, 0, 0])[:4]
    return parts[0], parts[1], parts[2], parts[3]


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: python packaging/make_version_info.py OUTPUT",
            file=sys.stderr,
        )
        return 2

    version = _version_tuple(__version__)
    dotted = ".".join(str(part) for part in version)
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version},
    prodvers={version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('FileDescription', 'Pseudocode PrettyPrint'),
        StringStruct('FileVersion', '{dotted}'),
        StringStruct('InternalName', 'PseudocodePrettyPrint'),
        StringStruct('LegalCopyright', 'MIT Licence'),
        StringStruct('OriginalFilename', 'PseudocodePrettyPrint.exe'),
        StringStruct('ProductName', 'Pseudocode PrettyPrint'),
        StringStruct('ProductVersion', '{dotted}'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
