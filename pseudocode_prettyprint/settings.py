"""Persistent desktop-app settings.

Settings live in the platform's normal per-user configuration directory so
the packaged application can remember the theme, font size, window geometry
and recent files between launches.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

APP_DIRECTORY = "PseudocodePrettyPrint"
_MAX_RECENT_FILES = 8
_MIN_FONT_SIZE = 9
_MAX_FONT_SIZE = 32


def config_directory() -> Path:
    """Return the per-user configuration directory for the app."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
    return base / APP_DIRECTORY


def settings_path() -> Path:
    """Return the full path of the settings file."""
    return config_directory() / "settings.json"


@dataclass
class Settings:
    """User-adjustable application state that survives restarts."""

    theme: str = "light"
    font_size: int = 13
    wrap: bool = True
    geometry: str = ""
    last_directory: str = ""
    recent_files: list[str] = field(default_factory=list)

    def remember_file(self, path: Path) -> None:
        """Record *path* as the most recent file, deduplicating the list."""
        resolved = Path(path).resolve()
        recent = [str(resolved)]
        for entry in self.recent_files:
            candidate = Path(entry).resolve()
            if candidate != resolved and str(candidate) not in recent:
                recent.append(str(candidate))
        self.recent_files = recent[:_MAX_RECENT_FILES]
        self.last_directory = str(resolved.parent)


def _as_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _as_text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _coerce_settings(raw: Any) -> Settings:
    """Build a valid Settings object from arbitrary decoded JSON."""
    defaults = Settings()
    if not isinstance(raw, dict):
        return defaults

    # Deep validation with type checking for each field
    validated_theme = _as_text(raw.get("theme"), defaults.theme)
    if validated_theme not in {"light", "dark"}:
        validated_theme = defaults.theme

    validated_font_size = _MIN_FONT_SIZE
    font_size_raw = raw.get("font_size")
    if isinstance(font_size_raw, int) and not isinstance(font_size_raw, bool):
        validated_font_size = max(_MIN_FONT_SIZE, min(_MAX_FONT_SIZE, font_size_raw))

    validated_recent_files: list[str] = []
    recent_raw = raw.get("recent_files")
    if isinstance(recent_raw, list):
        for entry in recent_raw:
            if isinstance(entry, str) and entry.strip() and (
                entry not in validated_recent_files
            ):
                validated_recent_files.append(entry)
    del validated_recent_files[_MAX_RECENT_FILES:]

    # Additional validation for geometry field (should be a string
    # representing window geometry)
    validated_geometry = _as_text(raw.get("geometry"), defaults.geometry)
    if len(validated_geometry) > 1000:  # Reasonable limit for geometry data
        validated_geometry = defaults.geometry

    # Validate last_directory as a non-empty path string or
    # empty string
    validated_last_directory = _as_text(
        raw.get("last_directory"), defaults.last_directory
    )
    if validated_last_directory and not validated_last_directory.strip():
        validated_last_directory = defaults.last_directory

    return Settings(
        theme=validated_theme,
        font_size=validated_font_size,
        wrap=_as_bool(raw.get("wrap"), defaults.wrap),
        geometry=validated_geometry,
        last_directory=validated_last_directory,
        recent_files=validated_recent_files,
    )


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, falling back to defaults for missing or bad files."""
    target = Path(path) if path is not None else settings_path()
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return Settings()
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        return Settings()
    return _coerce_settings(raw)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Atomically write *settings* to disk."""
    target = Path(path) if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(settings), indent=2, sort_keys=True) + "\n"

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.stem}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(
            file_descriptor, "w", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except BaseException:
        with contextlib.suppress(OSError):
            temporary_path.unlink()
        raise
