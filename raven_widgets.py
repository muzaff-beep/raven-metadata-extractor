"""
Reusable Tkinter widgets shared across the Raven GUI -- rebuilt on Canvas so
cards, pills, and buttons have TRUE rounded corners (Tkinter's stock Frame/
Label/Button are hard rectangles with no radius option at all).

Design tokens (colors, spacing) are centralized here so the whole app stays
visually consistent. Kept dependency-free (stdlib Tkinter only).
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

from raven_icons import draw_rounded_rect, draw_icon

# ---------------------------------------------------------------- design tokens
BG = "#1a1f24"
PANEL = "#242a30"
PANEL2 = "#2d343b"
PANEL_HOVER = "#333b43"
BORDER = "#39424a"
TEXT = "#eef1f3"
SUBTLE = "#8b96a0"
ACCENT = "#33a852"
ACCENT_HOVER = "#2c9647"

VERDICT_COLORS = {
    "likely_ai": "#e05c4e",
    "possibly_ai": "#e0a23e",
    "likely_camera": "#33a852",
    "inconclusive": "#6b7580",
}
VERDICT_LABELS = {
    "likely_ai": "Likely AI",
    "possibly_ai": "Possibly AI",
    "likely_camera": "Camera",
    "inconclusive": "Unknown",
}
TIER_COLORS = {
    "strong": "#e05c4e",
    "moderate": "#e0a23e",
    "weak": "#8b96a0",
    "info": "#4d9fd6",
}

RADIUS = 12          # standard corner radius for cards/panels
RADIUS_PILL = 999     # effectively fully-rounded (capped by draw_rounded_rect)
RADIUS_BTN = 8
SPACE = 4             # base spacing unit; use multiples of this (8, 12, 16, 20...)


def _safe_parent_bg(parent, default=BG):
    """
    Reads a parent widget's background color safely across both plain tk
    widgets (which use the "bg" option) and ttk themed widgets (which have
    NO "bg" option at all -- cget("bg") raises tkinter.TclError: unknown
    option "-bg" on a ttk.Frame/ttk.Label/etc). Falls back to `default` for
    ttk parents, non-widget parents, or anything else that goes wrong.
    """
    try:
        return parent.cget("bg")
    except (tk.TclError, AttributeError, TypeError):
        return default


class RoundedFrame(tk.Canvas):
    """
    A Canvas that draws a rounded rectangle background and behaves like a
    container: use .body to pack/grid child widgets inside it, same as a
    normal tk.Frame. This is the base for cards, panels, and pills.
    """
    def __init__(self, parent, bg_color=PANEL, radius=RADIUS, border_color=None,
                 border_width=1, width=None, height=None):
        parent_bg = _safe_parent_bg(parent)
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0,
                         width=width or 10, height=height or 10)
        self._bg_color = bg_color
        self._radius = radius
        self._border_color = border_color
        self._border_width = border_width
        self._rect_id = None

        self.body = tk.Frame(self, bg=bg_color)
        self._window_id = self.create_window(0, 0, window=self.body, anchor="nw")

        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        w, h = event.width, event.height
        if w < 2 or h < 2:
            return
        self.delete("bg_rect")
        kwargs = dict(fill=self._bg_color, outline=self._border_color or self._bg_color,
                     width=self._border_width, tags="bg_rect")
        draw_rounded_rect(self, 1, 1, w - 1, h - 1, self._radius, **kwargs)
        self.tag_lower("bg_rect")
        self.coords(self._window_id, 0, 0)
        self.itemconfig(self._window_id, width=w, height=h)


class DashboardCard(RoundedFrame):
    """
    Rounded icon + big number + label card, matching the mockup's top-row
    dashboard (Images / GPS / AI Flags / Cameras / C2PA). Icon is drawn as a
    small rounded color swatch with a vector line-icon on top (see
    raven_icons.py), not an emoji glyph or bundled image file.
    """
    def __init__(self, parent, icon: str, icon_color: str, value: str, label: str,
                 ui_font: str, sub: str = ""):
        super().__init__(parent, bg_color=PANEL, radius=RADIUS, border_color=BORDER)
        self.configure(height=118)

        top = tk.Frame(self.body, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(14, 4))

        badge = RoundedFrame(top, bg_color=icon_color, radius=9, width=32, height=32)
        badge.pack(side="left")
        badge.after_idle(lambda: draw_icon(badge, icon, 6, 6, 20, color="white", width=2.0))

        tk.Label(top, text=label, bg=PANEL, fg=SUBTLE, font=(ui_font, 9),
                 anchor="w").pack(side="left", padx=(10, 0))

        self.value_lbl = tk.Label(self.body, text=value, bg=PANEL, fg=TEXT,
                                  font=(ui_font, 24, "bold"), anchor="w")
        self.value_lbl.pack(fill="x", padx=16, pady=(0, 2 if sub else 14))
        if sub:
            tk.Label(self.body, text=sub, bg=PANEL, fg=SUBTLE, font=(ui_font, 8),
                     anchor="w").pack(fill="x", padx=16, pady=(0, 14))

    def set_value(self, value: str):
        self.value_lbl.config(text=value)


class Pill(RoundedFrame):
    """Small, genuinely rounded colored badge (real radius via Canvas, not a
    hard-cornered Frame with padding pretending to be one)."""
    def __init__(self, parent, text, color, ui_font, fg="white", size=9, bold=True):
        super().__init__(parent, bg_color=color, radius=RADIUS_PILL, height=26)
        lbl = tk.Label(self.body, text=text, bg=color, fg=fg,
                       font=(ui_font, size, "bold" if bold else "normal"))
        lbl.pack(padx=12, pady=4)
        self._resize_to_fit(lbl)

    def _resize_to_fit(self, lbl):
        # Deferred via after_idle: reading winfo_reqwidth() immediately after
        # pack() can return stale/unmapped geometry (Tk hasn't necessarily run
        # its geometry pass yet in the caller's context). after_idle runs once
        # Tk's own idle/geometry queue has actually processed the new widget.
        def _apply():
            try:
                w = lbl.winfo_reqwidth() + 24
                h = lbl.winfo_reqheight() + 8
                self.configure(width=max(w, 1), height=max(h, 1))
            except tk.TclError:
                pass  # widget destroyed before idle callback ran
        self.after_idle(_apply)


def verdict_pill(parent, verdict: str, score, ui_font: str) -> Pill:
    color = VERDICT_COLORS.get(verdict, VERDICT_COLORS["inconclusive"])
    label = VERDICT_LABELS.get(verdict, verdict)
    text = f"{label}" if score is None else f"{label} · {score}%"
    return Pill(parent, text, color, ui_font)


class RoundedButton(tk.Canvas):
    """
    A clickable rounded-rect button with hover feedback, replacing tk.Button
    (which cannot have rounded corners on any platform without owner-draw).
    """
    def __init__(self, parent, text, command=None, ui_font="TkDefaultFont",
                 bg_color=ACCENT, hover_color=None, fg="white", size=10,
                 padx=16, pady=9, bold=True, radius=RADIUS_BTN, icon=None):
        parent_bg = _safe_parent_bg(parent)
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0, cursor="hand2")
        self._command = command
        self._bg_color = bg_color
        self._hover_color = hover_color or bg_color
        self._radius = radius
        self._enabled = True
        self._icon = icon

        font = (ui_font, size, "bold" if bold else "normal")
        tmp = tk.Label(self, text=text, font=font)
        tmp.update_idletasks()
        text_w, text_h = tmp.winfo_reqwidth(), tmp.winfo_reqheight()
        tmp.destroy()

        icon_w = 22 if icon else 0
        if icon and not text:
            w = 16 + padx * 2  # icon-only: square-ish button, no reserved text space
        else:
            w = text_w + padx * 2 + icon_w
        h = text_h + pady * 2
        self.configure(width=w, height=h)

        self._draw(bg_color)
        if icon and not text:
            # Icon-only button: center the icon instead of reserving space to
            # its right for text that isn't there.
            icon_x = (w - 16) / 2
            draw_icon(self, icon, icon_x, (h - 16) / 2, 16, color=fg, width=2.0)
            self._text_id = self.create_text(w, h / 2, text="", fill=fg, font=font, anchor="w")
        else:
            text_x = padx + icon_w
            self._text_id = self.create_text(text_x, h / 2, text=text, fill=fg, font=font, anchor="w")
            if icon:
                draw_icon(self, icon, padx - 4, (h - 16) / 2, 16, color=fg, width=2.0)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, color):
        self.delete("bg_rect")
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        draw_rounded_rect(self, 0, 0, w, h, self._radius, fill=color, outline=color, tags="bg_rect")
        self.tag_lower("bg_rect")

    def _on_enter(self, _e):
        if self._enabled:
            self._draw(self._hover_color)

    def _on_leave(self, _e):
        if self._enabled:
            self._draw(self._bg_color)

    def _on_click(self, _e):
        if self._enabled and self._command:
            self._command()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._draw(self._bg_color if enabled else BORDER)
        self.configure(cursor="hand2" if enabled else "arrow")

    def set_text(self, text: str):
        self.itemconfig(self._text_id, text=text)


class TabbedPanel(tk.Frame):
    """
    Minimal tabbed container: a row of tab buttons + a content area that
    swaps between pre-built frames. Used by the detail modal for the
    EXIF / XMP / C2PA / Raw JSON tabs. Active tab gets an accent underline
    drawn on a thin Canvas strip rather than a background-color swap only,
    for a closer match to modern tab-strip designs.
    """
    def __init__(self, parent, ui_font: str):
        super().__init__(parent, bg=BG)
        self.ui_font = ui_font
        self._tabs: dict[str, dict] = {}
        self._active: str | None = None

        self.tab_bar = tk.Frame(self, bg=BG)
        self.tab_bar.pack(fill="x")
        self.underline = tk.Canvas(self, bg=BG, height=2, highlightthickness=0)
        self.underline.pack(fill="x")
        self.content_area = tk.Frame(self, bg=PANEL)
        self.content_area.pack(fill="both", expand=True)

        self._builders: dict = {}
        self._built: set = set()

    def add_tab(self, name: str, builder):
        btn = tk.Button(self.tab_bar, text=name, bg=BG, fg=SUBTLE, bd=0,
                        activebackground=BG, activeforeground=TEXT,
                        font=(self.ui_font, 9, "bold"), padx=16, pady=9,
                        relief="flat", cursor="hand2",
                        command=lambda: self.show(name))
        btn.pack(side="left")
        frame = tk.Frame(self.content_area, bg=PANEL)
        self._tabs[name] = {"btn": btn, "frame": frame}
        self._builders[name] = builder

    def show(self, name: str):
        if name not in self._tabs:
            return
        if name not in self._built:
            self._builders[name](self._tabs[name]["frame"])
            self._built.add(name)
        for n, t in self._tabs.items():
            if n == name:
                t["btn"].config(fg=TEXT)
                t["frame"].pack(fill="both", expand=True)
            else:
                t["btn"].config(fg=SUBTLE)
                t["frame"].pack_forget()
        self._active = name
        self.after_idle(self._draw_underline)

    def _draw_underline(self):
        self.underline.delete("all")
        btn = self._tabs.get(self._active, {}).get("btn")
        if not btn:
            return
        self.update_idletasks()
        x = btn.winfo_x()
        w = btn.winfo_width()
        self.underline.create_rectangle(x, 0, x + w, 2, fill=ACCENT, outline=ACCENT)
