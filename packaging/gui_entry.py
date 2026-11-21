"""PyInstaller entry point for the bundled desktop application.

PyInstaller runs the entry script as ``__main__`` rather than as part of the
package, so this file uses absolute imports and does no relative-import work.
"""

from pseudocode_prettyprint.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
