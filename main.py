#!/usr/bin/env python3
"""
Convert pseudocode from stdin (or a file) to RTF with syntax highlighting.

Usage:
  python3 main.py < input.txt
  python3 main.py input.txt
  python3 main.py                 # interactive mode

Equivalent console entry point (after installing the package):
  pseudocode-prettyprint input.txt
"""

import sys

from core.cli import main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # stdout was closed early (for example, piped into `head`).
        try:
            sys.stdout.close()
        except OSError:
            pass
        raise SystemExit(1)
