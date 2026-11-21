"""Native desktop interface for Pseudocode PrettyPrint.

The window is deliberately dependency-free: it uses Tkinter from the Python
standard library, so the packaged macOS and Windows builds have no runtime
requirements beyond the bundle itself.
"""

from __future__ import annotations

import contextlib
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Any, Literal

from pseudocode_prettyprint import __version__
from pseudocode_prettyprint.constants import COLOURS, KEYWORDS, Colour
from pseudocode_prettyprint.file_io import write_document, write_source
from pseudocode_prettyprint.highlight import highlight_tokens
from pseudocode_prettyprint.rtf import render_rtf
from pseudocode_prettyprint.settings import (
    Settings,
    load_settings,
    save_settings,
)
from pseudocode_prettyprint.tokeniser import (
    LexWarning,
    Token,
    TokeniseError,
    tokenise,
)

APP_NAME = "Pseudocode PrettyPrint"
_PROJECT_URL = "https://github.com/james8464/Pseudocode-PrettyPrint"
_MIN_FONT_SIZE = 9
_MAX_FONT_SIZE = 32
_PREVIEW_DELAY_MS = 120
_PREVIEW_LARGE_DELAY_MS = 350
_PREVIEW_CHAR_LIMIT = 120_000

_SAMPLE = """// Pseudocode PrettyPrint example
DECLARE total : INTEGER
DECLARE names : ARRAY[1:3] OF STRING

PROCEDURE Greet(name : STRING)
    OUTPUT "Hello, " & name
ENDPROCEDURE

names[1] ← "Ada"
names[2] ← "Alan"
names[3] ← "Grace"

total ← 0
FOR i ← 1 TO 3
    CALL Greet(names[i])
    total ← total + LENGTH(names[i])
NEXT i

OUTPUT "Total characters: ", total
"""


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


@dataclass(frozen=True)
class Palette:
    """Colours for one light or dark appearance."""

    window: str
    panel: str
    editor: str
    text: str
    muted: str
    border: str
    selection: str
    selection_text: str
    status: str
    accent: str
    accent_active: str
    button: str
    button_active: str
    error: str
    colours: dict[Colour, str]


_LIGHT = Palette(
    window="#F3F3F5",
    panel="#FFFFFF",
    editor="#FFFFFF",
    text="#262626",
    muted="#6E6E73",
    border="#D8D8DC",
    selection="#B9D9FF",
    selection_text="#000000",
    status="#ECECEF",
    accent="#0A6CFF",
    accent_active="#0057D8",
    button="#FFFFFF",
    button_active="#E9E9ED",
    error="#C7251B",
    colours={colour: _hex(rgb) for colour, rgb in COLOURS.items()},
)

_DARK = Palette(
    window="#1B1B1D",
    panel="#232326",
    editor="#1E1E20",
    text="#E8E8E8",
    muted="#9A9AA2",
    border="#3A3A3F",
    selection="#2F5D8A",
    selection_text="#FFFFFF",
    status="#202023",
    accent="#4C9AFF",
    accent_active="#6BB0FF",
    button="#2C2C31",
    button_active="#3A3A41",
    error="#FF6B5E",
    colours={
        Colour.BLACK: "#E8E8E8",
        Colour.STRING: "#FF8170",
        Colour.KEYWORD: "#FF7AB2",
        Colour.MEMBER: "#6BDFFF",
        Colour.INDEX: "#82AAFF",
        Colour.CALLABLE: "#C099FF",
        Colour.COMMENT: "#8A9199",
    },
)


def _pick_palette(name: str) -> Palette:
    return _DARK if name == "dark" else _LIGHT


class PseudocodeApp:
    """The main application window."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        initial_file: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.root = root
        self.settings = settings or load_settings()
        self.palette = _pick_palette(self.settings.theme)
        self._is_mac = root.tk.call("tk", "windowingsystem") == "aqua"
        self._primary = "Command" if self._is_mac else "Control"

        self._source_path: Path | None = None
        self._last_export_path: Path | None = None
        self._tokens: tuple[Token, ...] = ()
        self._warnings: tuple[LexWarning, ...] = ()
        self._preview_job: str | None = None
        self._preview_error = False
        self._preview_error_message = ""
        self._dirty = False
        self._find_window: tk.Toplevel | None = None
        self._find_entry: tk.Entry | None = None
        self._last_search = ""

        self._theme_var = tk.StringVar(value=self.settings.theme)
        self._wrap_var = tk.BooleanVar(value=self.settings.wrap)

        self._choose_fonts()
        self._configure_root()
        self._build_menu()
        self._build_interface()
        self._apply_theme()
        self._bind_shortcuts()
        self._restore_geometry()
        self._update_recent_menu()
        self._update_title()
        self._update_position()

        if initial_file is not None:
            self.root.after(80, lambda: self.open_path(initial_file))
        else:
            self.root.after(_PREVIEW_DELAY_MS, self._refresh_preview)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _choose_fonts(self) -> None:
        available = set(tkfont.families(self.root))
        family = ""
        for candidate in (
            "SF Mono",
            "Menlo",
            "Consolas",
            "Cascadia Mono",
            "DejaVu Sans Mono",
            "Liberation Mono",
            "Courier New",
        ):
            if candidate in available:
                family = candidate
                break
        if not family:
            family = str(tkfont.nametofont("TkFixedFont").actual("family"))

        self._ui_family = "SF Pro Text"
        if self._ui_family not in available:
            self._ui_family = "Helvetica" if self._is_mac else "Segoe UI"
        if self._ui_family not in available:
            self._ui_family = "TkDefaultFont"

        size = self.settings.font_size
        self.editor_font = tkfont.Font(
            root=self.root, family=family, size=size
        )
        self.bold_font = tkfont.Font(
            root=self.root, family=family, size=size, weight="bold"
        )

    def _configure_root(self) -> None:
        self.root.title(APP_NAME)
        self.root.minsize(780, 500)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

    def _make_button(
        self, parent: tk.Misc, text: str, command: Any, kind: str
    ) -> ttk.Button:
        button = ttk.Button(
            parent,
            text=text,
            command=command,
            style=f"{kind.title()}.TButton",
            cursor="hand2",
        )
        return button

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="Open…",
            accelerator=f"{self._primary}+O",
            command=self.open_file,
        )
        self._recent_menu = tk.Menu(file_menu, tearoff=False)
        file_menu.add_cascade(label="Open Recent", menu=self._recent_menu)
        file_menu.add_separator()
        file_menu.add_command(
            label="Save Pseudocode",
            accelerator=f"{self._primary}+S",
            command=self.save_source,
        )
        file_menu.add_command(
            label="Save Pseudocode As…",
            accelerator=f"{self._primary}+Shift+S",
            command=self.save_source_as,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Export RTF",
            accelerator=f"{self._primary}+E",
            command=self.save_rtf,
        )
        file_menu.add_command(
            label="Export RTF As…",
            command=self.save_rtf_as,
        )
        file_menu.add_command(
            label="Copy RTF to Clipboard",
            accelerator=f"{self._primary}+Shift+C",
            command=self.copy_rtf,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Quit",
            accelerator=f"{self._primary}+Q",
            command=self._on_close,
        )
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(
            label="Undo",
            accelerator=f"{self._primary}+Z",
            command=self._undo,
        )
        edit_menu.add_command(
            label="Redo",
            accelerator=f"{self._primary}+Shift+Z",
            command=self._redo,
        )
        edit_menu.add_separator()
        for label, sequence in (
            ("Cut", "<<Cut>>"),
            ("Copy", "<<Copy>>"),
            ("Paste", "<<Paste>>"),
        ):
            edit_menu.add_command(
                label=label,
                command=partial(self._editor_event, sequence),
            )
        edit_menu.add_command(
            label="Select All",
            accelerator=f"{self._primary}+A",
            command=self._select_all,
        )
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Find…",
            accelerator=f"{self._primary}+F",
            command=self._open_find,
        )
        edit_menu.add_command(
            label="Load Example",
            command=self.load_example,
        )
        edit_menu.add_command(label="Clear", command=self.clear_editor)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_radiobutton(
            label="Light Appearance",
            variable=self._theme_var,
            value="light",
            command=lambda: self._set_theme("light"),
        )
        view_menu.add_radiobutton(
            label="Dark Appearance",
            variable=self._theme_var,
            value="dark",
            command=lambda: self._set_theme("dark"),
        )
        view_menu.add_separator()
        view_menu.add_command(
            label="Larger Text",
            accelerator=f"{self._primary}++",
            command=lambda: self._change_font_size(1),
        )
        view_menu.add_command(
            label="Smaller Text",
            accelerator=f"{self._primary}+-",
            command=lambda: self._change_font_size(-1),
        )
        view_menu.add_command(
            label="Reset Text Size",
            accelerator=f"{self._primary}+0",
            command=lambda: self._set_font_size(13),
        )
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Word Wrap",
            variable=self._wrap_var,
            command=self._toggle_wrap,
        )
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label="Syntax Guide",
            accelerator="F1",
            command=self._show_syntax_guide,
        )
        help_menu.add_command(
            label="Warnings",
            command=self._show_warnings,
        )
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_interface(self) -> None:
        palette = self.palette

        self.header = tk.Frame(self.root, bg=palette.window)
        self.header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        self.header.columnconfigure(1, weight=1)

        self.title_label = tk.Label(
            self.header,
            text=APP_NAME,
            anchor="w",
            font=(self._ui_family, 18, "bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = tk.Label(
            self.header,
            text="Cambridge-style pseudocode  →  highlighted RTF",
            anchor="w",
            font=(self._ui_family, 11),
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.theme_button = self._make_button(
            self.header,
            "Dark mode",
            self._toggle_theme,
            "secondary",
        )
        self.theme_button.grid(row=0, column=2, rowspan=2, sticky="e")

        self.toolbar = tk.Frame(self.root, bg=palette.window)
        self.toolbar.grid(row=1, column=0, sticky="ew", padx=18, pady=(6, 10))

        self.open_button = self._make_button(
            self.toolbar, "Open", self.open_file, "secondary"
        )
        self.save_button = self._make_button(
            self.toolbar, "Save", self.save_source, "secondary"
        )
        self.export_button = self._make_button(
            self.toolbar, "Export RTF", self.save_rtf, "primary"
        )
        self.copy_button = self._make_button(
            self.toolbar, "Copy RTF", self.copy_rtf, "secondary"
        )
        self.example_button = self._make_button(
            self.toolbar, "Example", self.load_example, "secondary"
        )
        self.clear_button = self._make_button(
            self.toolbar, "Clear", self.clear_editor, "secondary"
        )
        for index, button in enumerate(
            (
                self.open_button,
                self.save_button,
                self.export_button,
                self.copy_button,
                self.example_button,
                self.clear_button,
            )
        ):
            button.grid(row=0, column=index, padx=(0, 6), sticky="w")

        self.main = tk.PanedWindow(
            self.root,
            orient="horizontal",
            sashwidth=7,
            sashrelief="flat",
            borderwidth=0,
            bg=palette.border,
        )
        self.main.grid(row=2, column=0, sticky="nsew", padx=18)

        self.editor_frame, self.editor = self._build_pane(
            self.main, "Pseudocode", editable=True
        )
        self.preview_frame, self.preview = self._build_pane(
            self.main, "Preview", editable=False
        )
        self.main.add(self.editor_frame, stretch="always")
        self.main.add(self.preview_frame, stretch="always")

        self.status_bar = tk.Frame(self.root, bg=palette.status)
        self.status_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.status_bar.columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            self.status_bar,
            text="Ready.",
            anchor="w",
            font=(self._ui_family, 10),
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=18, pady=5)

        self.position_label = tk.Label(
            self.status_bar,
            text="Ln 1, Col 1",
            anchor="e",
            font=(self._ui_family, 10),
        )
        self.position_label.grid(row=0, column=1, sticky="e", padx=18, pady=5)

        self.editor.bind("<<Modified>>", self._on_modified)
        self.editor.bind("<KeyRelease>", self._update_position)
        self.editor.bind("<ButtonRelease-1>", self._update_position)
        self.editor.bind("<Tab>", self._on_tab)
        self.editor.bind("<Shift-Tab>", self._on_shift_tab)
        self.editor.bind("<Return>", self._on_return)
        self.editor.bind("<Escape>", lambda _event: self._close_find())
        self.editor.focus_set()

    def _build_pane(
        self, parent: tk.Misc, title: str, *, editable: bool
    ) -> tuple[tk.Frame, tk.Text]:
        palette = self.palette
        frame = tk.Frame(
            parent,
            bg=palette.panel,
            highlightthickness=1,
            highlightbackground=palette.border,
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        label = tk.Label(
            frame,
            text=title.upper(),
            anchor="w",
            bg=palette.panel,
            fg=palette.muted,
            font=(self._ui_family, 9, "bold"),
            padx=12,
            pady=7,
        )
        label.grid(row=0, column=0, columnspan=2, sticky="ew")
        if title == "Pseudocode":
            self.editor_heading = label
        else:
            self.preview_heading = label

        text = tk.Text(
            frame,
            wrap="word" if self.settings.wrap else "none",
            undo=editable,
            maxundo=-1 if editable else 0,
            autoseparators=True,
            font=self.editor_font,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            tabs="4c",
            cursor="xterm" if editable else "arrow",
        )
        if not editable:
            text.configure(state="disabled", takefocus=0)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        horizontal = ttk.Scrollbar(
            frame, orient="horizontal", command=text.xview
        )
        text.configure(
            yscrollcommand=scrollbar.set,
            xscrollcommand=horizontal.set,
        )
        text.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        horizontal.grid(row=2, column=0, sticky="ew")

        if title == "Pseudocode":
            self.editor_horizontal = horizontal
            self.preview_horizontal = None
        else:
            self.preview_horizontal = horizontal
        if self.settings.wrap:
            horizontal.grid_remove()

        return frame, text

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        palette = self.palette
        self.root.configure(bg=palette.window)
        self.header.configure(bg=palette.window)
        self.toolbar.configure(bg=palette.window)

        self.title_label.configure(bg=palette.window, fg=palette.text)
        self.subtitle_label.configure(bg=palette.window, fg=palette.muted)

        self.main.configure(bg=palette.border)
        for frame in (self.editor_frame, self.preview_frame):
            frame.configure(bg=palette.panel, highlightbackground=palette.border)
        for label in (self.editor_heading, self.preview_heading):
            label.configure(bg=palette.panel, fg=palette.muted)

        for text in (self.editor, self.preview):
            text.configure(
                bg=palette.editor,
                fg=palette.text,
                insertbackground=palette.text,
                selectbackground=palette.selection,
                selectforeground=palette.selection_text,
            )

        self.status_bar.configure(bg=palette.status)
        self.status_label.configure(bg=palette.status, fg=palette.muted)
        self.position_label.configure(bg=palette.status, fg=palette.muted)

        self._configure_preview_tags()
        self._configure_ttk()
        self._refresh_theme_button()

    def _configure_ttk(self) -> None:
        palette = self.palette
        style = ttk.Style(self.root)
        with contextlib.suppress(tk.TclError):
            style.theme_use("clam")
        style.configure(
            "Primary.TButton",
            background=palette.accent,
            foreground="#FFFFFF",
            bordercolor=palette.accent,
            lightcolor=palette.accent,
            darkcolor=palette.accent,
            focuscolor=palette.accent,
            padding=(14, 7),
            font=(self._ui_family, 10),
            relief="flat",
        )
        style.map(
            "Primary.TButton",
            background=[
                ("pressed", palette.accent_active),
                ("active", palette.accent_active),
            ],
            foreground=[("disabled", palette.muted)],
        )
        style.configure(
            "Secondary.TButton",
            background=palette.button,
            foreground=palette.text,
            bordercolor=palette.border,
            lightcolor=palette.button,
            darkcolor=palette.button,
            focuscolor=palette.border,
            padding=(14, 7),
            font=(self._ui_family, 10),
            relief="flat",
        )
        style.map(
            "Secondary.TButton",
            background=[
                ("pressed", palette.button_active),
                ("active", palette.button_active),
            ],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=palette.button,
            troughcolor=palette.panel,
            bordercolor=palette.panel,
            arrowcolor=palette.muted,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", palette.button_active)],
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=palette.button,
            troughcolor=palette.panel,
            bordercolor=palette.panel,
            arrowcolor=palette.muted,
        )
        style.map(
            "Horizontal.TScrollbar",
            background=[("active", palette.button_active)],
        )

    def _configure_preview_tags(self) -> None:
        palette = self.palette
        for colour in Colour:
            self.preview.tag_configure(
                f"colour_{colour.value}",
                foreground=palette.colours[colour],
            )
        self.preview.tag_configure("bold", font=self.bold_font)
        self.preview.tag_configure("muted", foreground=palette.muted)
        self.preview.tag_configure("error", foreground=palette.error)
        self.editor.tag_configure(
            "find",
            background=palette.accent,
            foreground="#FFFFFF",
        )

    def _refresh_theme_button(self) -> None:
        label = "Light mode" if self.settings.theme == "dark" else "Dark mode"
        self.theme_button.configure(text=label)

    def _set_theme(self, theme: str) -> None:
        if theme not in {"light", "dark"}:
            return
        self.settings.theme = theme
        self._theme_var.set(theme)
        self.palette = _pick_palette(theme)
        self._apply_theme()
        self._persist_settings()
        self._refresh_preview()

    def _toggle_theme(self) -> None:
        self._set_theme("light" if self.settings.theme == "dark" else "dark")

    def _set_font_size(self, size: int) -> None:
        size = max(_MIN_FONT_SIZE, min(_MAX_FONT_SIZE, size))
        self.settings.font_size = size
        self.editor_font.configure(size=size)
        self.bold_font.configure(size=size)
        self._configure_preview_tags()
        self._persist_settings()

    def _change_font_size(self, delta: int) -> None:
        self._set_font_size(self.settings.font_size + delta)

    def _toggle_wrap(self) -> None:
        self.settings.wrap = bool(self._wrap_var.get())
        wrap: Literal["word", "none"] = (
            "word" if self.settings.wrap else "none"
        )
        self.editor.configure(wrap=wrap)
        self.preview.configure(wrap=wrap)
        for horizontal in (
            self.editor_horizontal,
            self.preview_horizontal,
        ):
            if horizontal is None:
                continue
            if self.settings.wrap:
                horizontal.grid_remove()
            else:
                horizontal.grid()
        self._persist_settings()

    # ------------------------------------------------------------------
    # Shortcuts and editor behaviour
    # ------------------------------------------------------------------

    def _bind(self, sequence: str, callback: Any) -> None:
        def handler(_event: object) -> str:
            callback()
            return "break"

        self.root.bind_all(sequence, handler)

    def _bind_shortcuts(self) -> None:
        primary = self._primary
        self._bind(f"<{primary}-o>", self.open_file)
        self._bind(f"<{primary}-s>", self.save_source)
        self._bind(f"<{primary}-Shift-S>", self.save_source_as)
        self._bind(f"<{primary}-e>", self.save_rtf)
        self._bind(f"<{primary}-Shift-C>", self.copy_rtf)
        self._bind(f"<{primary}-q>", self._on_close)
        self._bind(f"<{primary}-f>", self._open_find)
        self._bind(f"<{primary}-plus>", lambda: self._change_font_size(1))
        self._bind(f"<{primary}-equal>", lambda: self._change_font_size(1))
        self._bind(f"<{primary}-minus>", lambda: self._change_font_size(-1))
        self._bind(f"<{primary}-0>", lambda: self._set_font_size(13))
        self._bind("<F5>", self._refresh_preview)
        self._bind("<F1>", self._show_syntax_guide)

    def _editor_event(self, sequence: str) -> None:
        self.editor.focus_set()
        self.editor.event_generate(sequence)

    def _undo(self) -> None:
        self.editor.focus_set()
        with contextlib.suppress(tk.TclError):
            self.editor.edit_undo()

    def _redo(self) -> None:
        self.editor.focus_set()
        with contextlib.suppress(tk.TclError):
            self.editor.edit_redo()

    def _select_all(self) -> None:
        self.editor.focus_set()
        self.editor.tag_add("sel", "1.0", "end-1c")
        self.editor.mark_set("insert", "end-1c")

    def _on_tab(self, _event: object) -> str:
        self.editor.insert("insert", "    ")
        return "break"

    def _on_shift_tab(self, _event: object) -> str:
        line_start = self.editor.index("insert linestart")
        line_text = self.editor.get(line_start, "insert")
        if line_text.startswith("    "):
            self.editor.delete(line_start, f"{line_start}+4c")
        elif line_text.startswith("\t"):
            self.editor.delete(line_start, f"{line_start}+1c")
        return "break"

    def _on_return(self, _event: object) -> str:
        line_start = self.editor.index("insert linestart")
        line_text = self.editor.get(line_start, "insert")
        match = re.match(r"[ \t]*", line_text)
        indent = match.group(0) if match else ""
        self.editor.insert("insert", "\n" + indent)
        self.editor.see("insert")
        return "break"

    # ------------------------------------------------------------------
    # Document state
    # ------------------------------------------------------------------

    def _on_modified(self, _event: object = None) -> None:
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self._dirty = True
        self._update_title()
        self._schedule_preview()
        self._update_position()

    def _schedule_preview(self) -> None:
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
        length = len(self.editor.get("1.0", "end-1c"))
        delay = (
            _PREVIEW_LARGE_DELAY_MS
            if length > _PREVIEW_CHAR_LIMIT
            else _PREVIEW_DELAY_MS
        )
        self._preview_job = self.root.after(delay, self._refresh_preview)

    def _set_preview_message(self, text: str, tag: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text, tag)
        self.preview.configure(state="disabled")

    def _refresh_preview(self) -> None:
        self._preview_job = None
        source = self.editor.get("1.0", "end-1c")

        if not source.strip():
            self._preview_error = False
            self._preview_error_message = ""
            self._tokens = ()
            self._warnings = ()
            self._set_preview_message(
                "Your highlighted pseudocode will appear here.\n\n"
                "Open a file, paste some pseudocode, or load the example.",
                "muted",
            )
            self._set_status("Ready — open a file or start typing.")
            return

        try:
            result = tokenise(source)
        except TokeniseError as error:
            self._preview_error = True
            self._preview_error_message = str(error)
            self._tokens = ()
            self._warnings = ()
            self._set_preview_message(f"⚠  {error}", "error")
            self._set_status(f"Error: {error}", error=True)
            return

        self._preview_error = False
        self._preview_error_message = ""
        self._tokens = result.tokens
        self._warnings = result.warnings
        truncated = self._render_preview(result.tokens)

        message = f"Ready · {len(result.tokens):,} tokens"
        if result.warnings:
            message += f" · {len(result.warnings)} warning(s)"
        if truncated:
            message += " · preview limited"
        self._set_status(message)
        self._update_position()

    def _render_preview(self, tokens: tuple[Token, ...]) -> bool:
        """Render up to the preview limit; return whether it was truncated."""
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        budget = _PREVIEW_CHAR_LIMIT
        truncated = False
        for item in highlight_tokens(tokens):
            if len(item.text) > budget:
                truncated = True
                break
            start = self.preview.index("end-1c")
            self.preview.insert("end", item.text)
            end = self.preview.index("end-1c")
            if item.colour is not None:
                self.preview.tag_add(
                    f"colour_{item.colour.value}", start, end
                )
            if item.bold:
                self.preview.tag_add("bold", start, end)
            budget -= len(item.text)
        if truncated:
            self.preview.insert(
                "end",
                "\n\n… preview limited to the first "
                f"{_PREVIEW_CHAR_LIMIT:,} characters. "
                "Export still includes the whole document. …",
                "muted",
            )
        self.preview.configure(state="disabled")
        return truncated

    def _update_position(self, _event: object = None) -> None:
        line, column = self.editor.index("insert").split(".")
        count = len(self.editor.get("1.0", "end-1c"))
        self.position_label.configure(
            text=f"Ln {line}, Col {int(column) + 1}   ·   {count:,} chars"
        )

    def _update_title(self) -> None:
        name = self._source_path.name if self._source_path else "Untitled"
        marker = " •" if self._dirty else ""
        self.root.title(f"{name}{marker} — {APP_NAME}")

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, message: str, *, error: bool = False) -> None:
        self.status_label.configure(
            text=message,
            fg=self.palette.error if error else self.palette.muted,
        )

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def open_file(self) -> None:
        directory = self.settings.last_directory or str(Path.home())
        chosen = filedialog.askopenfilename(
            parent=self.root,
            title="Open pseudocode",
            initialdir=directory,
            filetypes=(
                ("Pseudocode", "*.txt *.pseudo *.pseudocode *.psc"),
                ("All files", "*.*"),
            ),
        )
        if chosen:
            self.open_path(Path(chosen))

    def open_path(self, path: Path) -> None:
        path = Path(path)
        if self._dirty and self.editor.get("1.0", "end-1c").strip():
            answer = messagebox.askyesnocancel(
                "Unsaved changes",
                f"Save the current text before opening {path.name}?",
                parent=self.root,
            )
            if answer is None:
                return
            if answer and not self.save_source():
                return
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            messagebox.showerror(
                "Cannot open file",
                f"{path.name} is not valid UTF-8.",
                parent=self.root,
            )
            return
        except OSError as error:
            messagebox.showerror(
                "Cannot open file",
                f"Could not read {path}:\n{error}",
                parent=self.root,
            )
            return

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.editor.tag_remove("find", "1.0", "end")
        self._dirty = False
        self._source_path = path
        self._last_export_path = None
        self.settings.remember_file(path)
        self._persist_settings()
        self._update_title()
        self._update_recent_menu()
        self._refresh_preview()
        self._set_status(f"Opened {path.name}")
        self.editor.focus_set()

    def _default_source_name(self) -> str:
        if self._source_path is not None:
            return self._source_path.name
        return "pseudocode.txt"

    def save_source(self) -> bool:
        if self._source_path is not None:
            return self._write_source_to(self._source_path)
        return self.save_source_as()

    def save_source_as(self) -> bool:
        directory = self.settings.last_directory or str(Path.home())
        chosen = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save pseudocode",
            defaultextension=".txt",
            initialdir=directory,
            initialfile=self._default_source_name(),
            filetypes=(
                ("Pseudocode", "*.txt *.pseudo *.pseudocode *.psc"),
                ("All files", "*.*"),
            ),
        )
        if not chosen:
            return False
        return self._write_source_to(Path(chosen))

    def _write_source_to(self, path: Path) -> bool:
        text = self.editor.get("1.0", "end-1c")
        try:
            write_source(path, text)
        except OSError as error:
            messagebox.showerror(
                "Cannot save pseudocode",
                f"Could not write {path}:\n{error}",
                parent=self.root,
            )
            return False

        if self._source_path != path:
            self._last_export_path = None
        self._source_path = path
        self._dirty = False
        self.editor.edit_modified(False)
        self.settings.remember_file(path)
        self._persist_settings()
        self._update_title()
        self._update_recent_menu()
        self._set_status(f"Saved {path.name}")
        return True

    def _default_export_name(self) -> str:
        if self._source_path is not None:
            return f"{self._source_path.stem}.rtf"
        return "pretty_pseudocode.rtf"

    def save_rtf(self) -> bool:
        if self._last_export_path is not None:
            return self._write_to(self._last_export_path)
        return self.save_rtf_as()

    def save_rtf_as(self) -> bool:
        if not self._prepare_export():
            return False
        directory = self.settings.last_directory or str(Path.home())
        chosen = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export RTF",
            defaultextension=".rtf",
            initialdir=directory,
            initialfile=self._default_export_name(),
            filetypes=(("Rich Text Format", "*.rtf"), ("All files", "*.*")),
        )
        if not chosen:
            return False
        return self._write_to(Path(chosen))

    def _prepare_export(self) -> bool:
        self._refresh_preview()
        if self._preview_error:
            messagebox.showerror(
                "Cannot export",
                self._preview_error_message,
                parent=self.root,
            )
            return False
        if not self._tokens:
            messagebox.showinfo(
                "Nothing to export",
                "There is no pseudocode to export yet.",
                parent=self.root,
            )
            return False
        return True

    def _write_to(self, path: Path) -> bool:
        if not self._prepare_export():
            return False
        try:
            write_document(path, self._tokens)
        except (OSError, UnicodeEncodeError) as error:
            messagebox.showerror(
                "Cannot save output",
                f"Could not write {path}:\n{error}",
                parent=self.root,
            )
            return False

        self._last_export_path = path
        self.settings.last_directory = str(path.parent)
        self._persist_settings()
        self._set_status(f"Exported {path.name}")
        return True

    def copy_rtf(self) -> None:
        if not self._prepare_export():
            return
        document = render_rtf(self._tokens)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(document)
            self.root.update_idletasks()
        except tk.TclError as error:
            messagebox.showerror(
                "Cannot copy",
                f"The clipboard is unavailable:\n{error}",
                parent=self.root,
            )
            return
        self._set_status("RTF copied to the clipboard.")

    def load_example(self) -> None:
        current = self.editor.get("1.0", "end-1c")
        if current.strip() and not messagebox.askyesno(
            "Load example",
            "Replace the current text with the example?",
            parent=self.root,
        ):
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", _SAMPLE)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._dirty = True
        self._source_path = None
        self._last_export_path = None
        self._update_title()
        self._refresh_preview()
        self._set_status("Example loaded.")
        self.editor.focus_set()

    def clear_editor(self) -> None:
        current = self.editor.get("1.0", "end-1c")
        if current.strip() and not messagebox.askyesno(
            "Clear editor",
            "Clear all text?",
            parent=self.root,
        ):
            return
        self.editor.delete("1.0", "end")
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._dirty = False
        self._source_path = None
        self._last_export_path = None
        self._update_title()
        self._refresh_preview()
        self._set_status("Editor cleared.")
        self.editor.focus_set()

    def _update_recent_menu(self) -> None:
        self._recent_menu.delete(0, "end")
        existing = [
            entry for entry in self.settings.recent_files if Path(entry).is_file()
        ]
        if not existing:
            self._recent_menu.add_command(
                label="No recent files", state="disabled"
            )
            return
        for entry in existing:
            self._recent_menu.add_command(
                label=Path(entry).name,
                command=partial(self.open_path, Path(entry)),
            )
        self._recent_menu.add_separator()
        self._recent_menu.add_command(
            label="Clear Recent",
            command=self._clear_recent,
        )

    def _clear_recent(self) -> None:
        self.settings.recent_files.clear()
        self._persist_settings()
        self._update_recent_menu()
        self._set_status("Recent files cleared.")

    # ------------------------------------------------------------------
    # Find
    # ------------------------------------------------------------------

    def _open_find(self) -> None:
        if (
            self._find_window is not None
            and self._find_window.winfo_exists()
        ):
            self._find_window.lift()
            if self._find_entry is not None:
                self._find_entry.focus_set()
            return

        palette = self.palette
        window = tk.Toplevel(self.root)
        window.title("Find")
        window.transient(self.root)
        window.resizable(False, False)
        window.configure(bg=palette.panel)

        frame = tk.Frame(window, bg=palette.panel, padx=14, pady=12)
        frame.pack(fill="both", expand=True)
        label = tk.Label(
            frame,
            text="Find in pseudocode",
            bg=palette.panel,
            fg=palette.muted,
            font=(self._ui_family, 10),
        )
        label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        entry = tk.Entry(
            frame,
            width=32,
            font=(self._ui_family, 11),
            bg=palette.editor,
            fg=palette.text,
            insertbackground=palette.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=palette.border,
            highlightcolor=palette.accent,
        )
        entry.grid(row=1, column=0, columnspan=2, sticky="ew")
        entry.insert(0, self._last_search)
        entry.select_range(0, "end")

        find_button = self._make_button(
            frame, "Find Next", self._find_next, "primary"
        )
        find_button.grid(row=2, column=0, sticky="w", pady=(10, 0))
        close_button = self._make_button(
            frame, "Close", self._close_find, "secondary"
        )
        close_button.grid(row=2, column=1, sticky="e", pady=(10, 0))

        entry.bind("<Return>", lambda _event: self._find_next())
        entry.bind("<Escape>", lambda _event: self._close_find())
        window.protocol("WM_DELETE_WINDOW", self._close_find)

        self._find_window = window
        self._find_entry = entry
        entry.focus_set()

    def _close_find(self) -> None:
        if self._find_window is not None:
            with contextlib.suppress(tk.TclError):
                self._find_window.destroy()
        self._find_window = None
        self._find_entry = None
        self.editor.focus_set()

    def _find_next(self) -> None:
        if self._find_entry is None:
            return
        needle = self._find_entry.get()
        if not needle:
            return
        self._last_search = needle
        self.editor.tag_remove("find", "1.0", "end")
        start = self.editor.index("insert")
        found = self.editor.search(
            needle, start, stopindex="end", nocase=True
        )
        if not found:
            found = self.editor.search(
                needle, "1.0", stopindex="end", nocase=True
            )
        if not found:
            self._set_status(f"No match for {needle!r}.", error=True)
            return
        end = f"{found}+{len(needle)}c"
        self.editor.tag_add("find", found, end)
        self.editor.mark_set("insert", end)
        self.editor.see(found)
        self.editor.focus_set()
        self._set_status(f"Found {needle!r}.")

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _show_syntax_guide(self) -> None:
        palette = self.palette
        window = tk.Toplevel(self.root)
        window.title("Syntax guide")
        window.transient(self.root)
        window.geometry("640x480")
        window.configure(bg=palette.panel)

        text = tk.Text(
            window,
            wrap="word",
            padx=16,
            pady=14,
            bg=palette.editor,
            fg=palette.text,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=(self._ui_family, 11),
        )
        text.pack(fill="both", expand=True)
        guide = (
            "Highlighting\n\n"
            "Keywords and built-ins are bold. Procedure, function, class and "
            "type names are recognised from declarations, from CALL, NEW and "
            "INHERITS, and from an identifier followed by an opening "
            "parenthesis.\n\n"
            "Members after a dot are blue; numeric indices after a dot are "
            "dark blue; comments are grey; strings are red.\n\n"
            "Keywords and built-ins\n\n"
            + ", ".join(sorted(KEYWORDS))
            + "\n\nInput\n\n"
            "Tabs are supported. Strings use double quotes (straight or "
            "curly) and cannot span a line. Comments start with //.\n\n"
            "Export\n\n"
            "Save RTF writes a document you can open in Word, Pages or "
            "LibreOffice. Copy RTF puts the markup on the clipboard.\n"
        )
        text.insert("1.0", guide)
        text.configure(state="disabled")

    def _show_warnings(self) -> None:
        self._refresh_preview()
        if self._preview_error:
            messagebox.showerror(
                "Cannot check input",
                self._preview_error_message,
                parent=self.root,
            )
            return
        if not self._warnings:
            messagebox.showinfo(
                "Warnings", "No warnings in this document.", parent=self.root
            )
            return
        shown = self._warnings[:50]
        detail = "\n".join(str(warning) for warning in shown)
        remaining = len(self._warnings) - len(shown)
        if remaining:
            detail += f"\n…and {remaining} more."
        messagebox.showwarning("Warnings", detail, parent=self.root)

    def _show_about(self) -> None:
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} {__version__}\n\n"
            "Cambridge-style pseudocode to syntax-highlighted RTF.\n\n"
            f"{_PROJECT_URL}",
            parent=self.root,
        )

    # ------------------------------------------------------------------
    # Persistence and shutdown
    # ------------------------------------------------------------------

    def _restore_geometry(self) -> None:
        geometry = self.settings.geometry
        if re.fullmatch(r"\d+x\d+([+-]\d+){2}", geometry):
            self.root.geometry(geometry)
            return
        width = min(1120, self.root.winfo_screenwidth() - 80)
        height = min(720, self.root.winfo_screenheight() - 140)
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(20, (self.root.winfo_screenheight() - height) // 2 - 20)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _persist_settings(self) -> None:
        with contextlib.suppress(OSError):
            save_settings(self.settings)

    def _on_close(self) -> None:
        if self._dirty and self.editor.get("1.0", "end-1c").strip():
            answer = messagebox.askyesnocancel(
                "Unsaved changes",
                "Save your pseudocode before closing?",
                parent=self.root,
            )
            if answer is None:
                return
            if answer and not self.save_source():
                return
        self.settings.geometry = self.root.geometry()
        self._persist_settings()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    """Launch the desktop application."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in {"-h", "--help"}:
        print(
            "usage: pseudocode-prettyprint-gui [FILE]\n\n"
            "Open the Pseudocode PrettyPrint desktop app, optionally with a\n"
            "pseudocode file to load."
        )
        return 0
    if arguments and arguments[0] == "--version":
        print(f"pseudocode-prettyprint-gui {__version__}")
        return 0
    if len(arguments) > 1:
        print(
            "Error: only one file can be opened at a time",
            file=sys.stderr,
        )
        return 2

    initial_file: Path | None = None
    if arguments:
        candidate = Path(arguments[0]).expanduser()
        if not candidate.exists():
            print(f"Error: {candidate} does not exist", file=sys.stderr)
            return 1
        initial_file = candidate

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(
            "Error: could not start the desktop interface: "
            f"{error}",
            file=sys.stderr,
        )
        print(
            "Use the command-line interface instead: "
            "pseudocode-prettyprint --help",
            file=sys.stderr,
        )
        return 1

    PseudocodeApp(root, initial_file=initial_file)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
