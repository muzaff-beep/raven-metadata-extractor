"""
Reusable Tkinter widgets shared across the Raven GUI: icon dashboard cards,
colored verdict/status pills, and a simple tabbed container (used by the
detail modal for EXIF / XMP / C2PA / Raw JSON tabs).

Kept dependency-free (stdlib Tkinter only) so the GUI still runs with just
Pillow/exifread/numpy installed.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

BG = "#1e2327"
PANEL = "#262d33"
PANEL2 = "#2f373f"
BORDER = "#3a434b"
TEXT = "#e6e6e6"
SUBTLE = "#8a939b"
ACCENT = "#2e7d32"

VERDICT_COLORS = {
    "likely_ai": "#c0392b",
    "possibly_ai": "#d98324",
    "likely_camera": "#2e7d32",
    "inconclusive": "#5c6670",
}
VERDICT_LABELS = {
    "likely_ai": "Likely AI",
    "possibly_ai": "Possibly AI",
    "likely_camera": "Camera",
    "inconclusive": "Unknown",
}
TIER_COLORS = {
    "strong": "#c0392b",
    "moderate": "#d98324",
    "weak": "#8a939b",
    "info": "#4a90c2",
}


class DashboardCard(tk.Frame):
    """
    An icon + big number + label card, matching the mockup's top-row
    dashboard (Images / GPS / AI Flags / Cameras / C2PA).
    Tkinter has no emoji-icon font guarantee across all platforms, so we
    accept a short glyph/emoji string and fall back gracefully if the font
    can't render it (shows as a tofu box at worst, never crashes).
    """
    def __init__(self, parent, icon: str, icon_color: str, value: str, label: str,
                 ui_font: str, sub: str = ""):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top = tk.Frame(self, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(12, 2))

        icon_badge = tk.Frame(top, bg=icon_color, width=30, height=30)
        icon_badge.pack(side="left")
        icon_badge.pack_propagate(False)
        tk.Label(icon_badge, text=icon, bg=icon_color, fg="white",
                 font=(ui_font, 13)).place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(top, text=label, bg=PANEL, fg=SUBTLE, font=(ui_font, 9),
                 anchor="w").pack(side="left", padx=(10, 0))

        tk.Label(self, text=value, bg=PANEL, fg=TEXT, font=(ui_font, 22, "bold"),
                 anchor="w").pack(fill="x", padx=14, pady=(0, 2 if sub else 12))
        if sub:
            tk.Label(self, text=sub, bg=PANEL, fg=SUBTLE, font=(ui_font, 8),
                     anchor="w").pack(fill="x", padx=14, pady=(0, 12))

    def set_value(self, value: str):
        # value label is the 3rd child packed (index after top row)
        for child in self.winfo_children():
            if isinstance(child, tk.Label) and child.cget("font") and "22" in str(child.cget("font")):
                child.config(text=value)
                return


class Pill(tk.Frame):
    """Small rounded-looking colored badge (Tk has no true rounded rects at
    this size without Canvas tricks, so padding + solid color reads as a pill)."""
    def __init__(self, parent, text, color, ui_font, fg="white", size=9, bold=True):
        super().__init__(parent, bg=color)
        tk.Label(self, text=text, bg=color, fg=fg,
                 font=(ui_font, size, "bold" if bold else "normal"),
                 padx=10, pady=4).pack()


def verdict_pill(parent, verdict: str, score, ui_font: str) -> Pill:
    color = VERDICT_COLORS.get(verdict, VERDICT_COLORS["inconclusive"])
    label = VERDICT_LABELS.get(verdict, verdict)
    text = f"{label}" if score is None else f"{label} · {score}%"
    return Pill(parent, text, color, ui_font)


class TabbedPanel(tk.Frame):
    """
    Minimal tabbed container: a row of tab buttons + a content area that
    swaps between pre-built frames. Used by the detail modal for the
    EXIF / XMP / C2PA / Raw JSON tabs seen in the mockup.

    Usage:
        tp = TabbedPanel(parent, ui_font)
        tp.add_tab("EXIF", build_func_that_returns_a_frame)
        tp.add_tab("XMP", other_build_func)
        tp.pack(fill="both", expand=True)
        tp.show("EXIF")
    """
    def __init__(self, parent, ui_font: str):
        super().__init__(parent, bg=BG)
        self.ui_font = ui_font
        self._tabs: dict[str, tuple[tk.Button, tk.Frame]] = {}
        self._active: str | None = None

        self.tab_bar = tk.Frame(self, bg=BG)
        self.tab_bar.pack(fill="x")
        self.content_area = tk.Frame(self, bg=PANEL)
        self.content_area.pack(fill="both", expand=True)

    def add_tab(self, name: str, builder):
        """builder(parent_frame) -> populates the frame; called lazily on first show."""
        btn = tk.Button(self.tab_bar, text=name, bg=BG, fg=SUBTLE, bd=0,
                        activebackground=PANEL2, activeforeground=TEXT,
                        font=(self.ui_font, 9, "bold"), padx=14, pady=8,
                        relief="flat", cursor="hand2",
                        command=lambda: self.show(name))
        btn.pack(side="left")
        frame = tk.Frame(self.content_area, bg=PANEL)
        self._tabs[name] = (btn, frame)
        self._builders = getattr(self, "_builders", {})
        self._builders[name] = builder
        self._built = getattr(self, "_built", set())

    def show(self, name: str):
        if name not in self._tabs:
            return
        if name not in self._built:
            self._builders[name](self._tabs[name][1])
            self._built.add(name)
        for n, (btn, frame) in self._tabs.items():
            if n == name:
                btn.config(bg=PANEL2, fg=TEXT, highlightbackground=ACCENT)
                frame.pack(fill="both", expand=True)
            else:
                btn.config(bg=BG, fg=SUBTLE)
                frame.pack_forget()
        self._active = name
