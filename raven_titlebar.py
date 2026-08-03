"""
Custom title bar for Windows only, matching the target mockup (app icon +
title on the left, minimize/maximize/restore/close on the right, draggable).

macOS and Linux keep the native OS title bar -- overrideredirect() has real
platform quirks (reduced native feel on macOS, inconsistent behavior across
Linux window managers), so the custom bar is deliberately scoped to Windows
only, where it's reliable.

Usage: call `attach_custom_title_bar(app)` once, after RavenApp's normal
init. On non-Windows platforms this is a no-op -- the native title bar is
left completely alone.
"""
from __future__ import annotations
import os
import sys
import tkinter as tk

from raven_widgets import BG, PANEL, PANEL2, TEXT, SUBTLE, BORDER
from raven_icons import draw_icon


TITLE_BAR_HEIGHT = 32
_BTN_WIDTH = 46


def is_supported() -> bool:
    return os.name == "nt" and sys.platform == "win32"


def attach_custom_title_bar(app: tk.Tk, title: str = "Raven Metadata Extractor"):
    """
    Replaces the native Windows title bar with a custom-drawn one matching
    the mockup. No-op on macOS/Linux (native title bar untouched).

    Must be called AFTER app.title()/app.geometry() have been set, and before
    other widgets are packed, so the custom bar sits at the very top.
    """
    if not is_supported():
        return  # native title bar stays exactly as-is on macOS/Linux

    app.overrideredirect(True)
    bar = _CustomTitleBar(app, title)
    bar.pack(side="top", fill="x")
    app._custom_title_bar = bar  # keep a reference; also lets callers restyle later
    return bar


class _CustomTitleBar(tk.Frame):
    def __init__(self, app: tk.Tk, title: str):
        super().__init__(app, bg=PANEL, height=TITLE_BAR_HEIGHT)
        self.app = app
        self.pack_propagate(False)
        self._is_maximized = False
        self._restore_geometry = None
        self._drag_start = None

        # ---- left: app icon (if available) + title text ---------------------
        left = tk.Frame(self, bg=PANEL)
        left.pack(side="left", fill="y", padx=(10, 0))

        self._icon_imgtk = self._load_title_icon()
        if self._icon_imgtk:
            tk.Label(left, image=self._icon_imgtk, bg=PANEL).pack(side="left", pady=6, padx=(0, 8))

        tk.Label(left, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 9)).pack(
            side="left", pady=6)

        # ---- right: minimize / maximize / close --------------------------------
        right = tk.Frame(self, bg=PANEL)
        right.pack(side="right", fill="y")

        self._make_btn(right, "minimize", self._on_minimize, hover_color=PANEL2)
        self._maximize_canvas = self._make_btn(right, "maximize", self._on_maximize_restore,
                                               hover_color=PANEL2)
        self._make_btn(right, "close", self._on_close, hover_color="#c0392b")

        # ---- draggable area: the bar itself + the title label (not the buttons) --
        for widget in (self, left):
            widget.bind("<ButtonPress-1>", self._drag_start_evt)
            widget.bind("<B1-Motion>", self._drag_motion_evt)
        self.bind("<Double-Button-1>", lambda e: self._on_maximize_restore())

    # ------------------------------------------------------------------ icon
    def _load_title_icon(self):
        from raven_gui import APP_ICON_PNG_PATH
        if not os.path.isfile(APP_ICON_PNG_PATH):
            return None
        try:
            from PIL import Image, ImageTk
            with Image.open(APP_ICON_PNG_PATH) as im:
                im = im.convert("RGBA")
                im.thumbnail((18, 18))
                return ImageTk.PhotoImage(im)
        except Exception:
            return None

    # ------------------------------------------------------------------ buttons
    def _make_btn(self, parent, icon_name: str, command, hover_color: str) -> tk.Canvas:
        c = tk.Canvas(parent, width=_BTN_WIDTH, height=TITLE_BAR_HEIGHT, bg=PANEL,
                      highlightthickness=0, bd=0, cursor="arrow")
        c.pack(side="left", fill="y")

        bg_id = c.create_rectangle(0, 0, _BTN_WIDTH, TITLE_BAR_HEIGHT, fill=PANEL,
                                   outline=PANEL, tags="bg")
        c.tag_lower(bg_id)
        self._draw_glyph(c, icon_name)

        def on_enter(_e):
            c.itemconfig("bg", fill=hover_color, outline=hover_color)
        def on_leave(_e):
            c.itemconfig("bg", fill=PANEL, outline=PANEL)
        def on_click(_e):
            command()

        c.bind("<Enter>", on_enter)
        c.bind("<Leave>", on_leave)
        c.bind("<Button-1>", on_click)
        return c

    def _draw_glyph(self, canvas: tk.Canvas, kind: str):
        canvas.delete("glyph")
        cx, cy = _BTN_WIDTH / 2, TITLE_BAR_HEIGHT / 2
        if kind == "minimize":
            canvas.create_line(cx - 5, cy, cx + 5, cy, fill=TEXT, width=1.4,
                              capstyle="round", tags="glyph")
        elif kind == "maximize":
            if self._is_maximized:
                # restore glyph: two overlapping squares
                canvas.create_rectangle(cx - 5, cy - 3, cx + 2, cy + 4, outline=TEXT,
                                       width=1.2, tags="glyph")
                canvas.create_rectangle(cx - 2, cy - 5, cx + 5, cy + 2, outline=TEXT,
                                       width=1.2, fill=PANEL, tags="glyph")
            else:
                canvas.create_rectangle(cx - 5, cy - 5, cx + 5, cy + 5, outline=TEXT,
                                       width=1.2, tags="glyph")
        elif kind == "close":
            canvas.create_line(cx - 5, cy - 5, cx + 5, cy + 5, fill=TEXT, width=1.4,
                              capstyle="round", tags="glyph")
            canvas.create_line(cx + 5, cy - 5, cx - 5, cy + 5, fill=TEXT, width=1.4,
                              capstyle="round", tags="glyph")

    # ------------------------------------------------------------------ actions
    def _on_minimize(self):
        # overrideredirect windows can't use the normal iconify path reliably
        # on Windows; withdraw + a taskbar-visible re-show via a short
        # overrideredirect toggle is the standard workaround.
        self.app.overrideredirect(False)
        self.app.iconify()

        def _on_restore(event=None):
            self.app.overrideredirect(True)
            self.app.unbind("<Map>")
        self.app.bind("<Map>", _on_restore)

    def _on_maximize_restore(self):
        if self._is_maximized:
            if self._restore_geometry:
                self.app.geometry(self._restore_geometry)
            self._is_maximized = False
        else:
            self._restore_geometry = self.app.geometry()
            sw = self.app.winfo_screenwidth()
            sh = self.app.winfo_screenheight()
            # Leave room for the Windows taskbar rather than covering it.
            self.app.geometry(f"{sw}x{sh - 48}+0+0")
            self._is_maximized = True
        self._draw_glyph(self._maximize_canvas, "maximize")

    def _on_close(self):
        self.app.destroy()

    # ------------------------------------------------------------------ drag
    def _drag_start_evt(self, event):
        self._drag_start = (event.x_root, event.y_root,
                           self.app.winfo_x(), self.app.winfo_y())

    def _drag_motion_evt(self, event):
        if not self._drag_start:
            return
        sx, sy, wx, wy = self._drag_start
        dx, dy = event.x_root - sx, event.y_root - sy
        self.app.geometry(f"+{wx + dx}+{wy + dy}")
