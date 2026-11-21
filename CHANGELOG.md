# Changelog

## 1.2.0

### Added

- Native desktop app for macOS and Windows with a live syntax-highlighted
  preview.
- Light and dark appearances, adjustable text size, word wrap, find, recent
  files, a warnings viewer, and a syntax guide.
- Save the pseudocode source as UTF-8, or export the highlighted RTF, and copy
  RTF markup to the clipboard.
- Unsaved-change protection when opening another file or closing the window.
- `pseudocode-prettyprint-gui` console entry point, `python -m
  pseudocode_prettyprint.gui`, and a `--gui` flag on the command-line tool.
- Persistent per-user settings for theme, text size, window geometry, and
  recent files.
- GitHub Actions release workflow producing `.dmg` builds for Apple silicon
  and Intel Macs, and a Windows `.zip`.

### Changed

- Syntax classification now lives in `highlight.py` and is shared by the RTF
  renderer and the desktop preview, so the two cannot drift apart.
- The version is now 1.2.0.

## 1.1.0

- Added `pyproject.toml`, console entry point, `py.typed`, MIT licence, and
  multi-version CI.
- Renamed the `core` package to `pseudocode_prettyprint`.
- Added the command-line interface, UTF-8 input, atomic output, and
  non-overwriting file names.
- Added the regression suite, ruff and mypy configuration, and the rewritten
  README.

## 1.0.0

- Initial RTF renderer with syntax highlighting, interactive mode, and
  colour-table generation.
