#!/usr/bin/env python3
"""
Reads pseudocode from stdin, writes RTF with syntax highlighting.

Usage:
  python3 main.py < input.txt
  # or run and paste, finish with END on its own line
  python3 main.py
"""

import sys

from core.file_io import process_input, read_input


def main() -> int:
    # if input is piped, process once and exit
    if not sys.stdin.isatty():
        _text = read_input()
        if _text:
            process_input(_text, 1)
        return 0

    # interactive loop mode
    _counter = 0
    print("Pseudocode formatter - interactive mode")
    print("=" * 40)
    
    while True:
        _counter += 1
        _text = read_input()
        
        if _text is None:
            print("Exiting...")
            break
        
        if not _text.strip():
            _counter -= 1
            continue
        
        process_input(_text, _counter)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
