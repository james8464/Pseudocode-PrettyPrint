#!/usr/bin/env python3
"""
Convert pseudocode from stdin (or a file) to RTF with syntax highlighting.

Usage:
  python3 main.py < input.txt
  python3 main.py input.txt
  python3 main.py                 # interactive mode
  python3 main.py --gui           # desktop app

Equivalent console entry points (after installing the package):
  pseudocode-prettyprint input.txt
  pseudocode-prettyprint-gui
"""

import contextlib
import sys

from pseudocode_prettyprint.cli import main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # stdout was closed early (for example, piped into `head`).
        with contextlib.suppress(OSError):
            sys.stdout.close()
        raise SystemExit(1) from None
