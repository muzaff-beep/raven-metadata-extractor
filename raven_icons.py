"""
Canvas-drawing primitives for the polished Raven GUI:
  - draw_rounded_rect: true rounded rectangles (Tk has no native support)
  - ICON_DRAW_FUNCS: a small set of line icons drawn directly on Canvas in
    Lucide's visual style (2px stroke, round caps/joins, 24x24 grid) --
    vector-drawn rather than bundled image/font files, so there's no new
    dependency (no cairosvg, no icon font, no network fetch) and icons stay
    crisp at any size and any DPI.

Lucide itself (https://lucide.dev) is ISC-licensed and free to use; these are
small original redraws in the same stroke-icon style, not copies of Lucide's
SVG paths, since we can't ship SVG files without an SVG rasterizer dependency.
"""
from __future__ import annotations
import tkinter as tk
import math


def draw_rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, radius, **kwargs):
    """
    Draws a true rounded rectangle on a Canvas using a smoothed polygon
    (Tkinter has no native rounded-rect primitive). Returns the item id.
    kwargs forwarded to create_polygon (fill, outline, width, etc).
    """
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def _stroke_kwargs(color, width=2.0):
    return dict(fill=color, width=width, capstyle="round", joinstyle="round")


def _icon_image(icon: str, size: int, x: int, y: int) -> str:
    return icon, size, x, y


# ---------------------------------------------------------------------------
# Each function draws its icon inside a size x size box with top-left at (x, y),
# using strokes only (no fills) to match Lucide's line-icon style.
# ---------------------------------------------------------------------------

def icon_image(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    k = _stroke_kwargs(color, width)
    # picture frame
    canvas.create_rectangle(x + s*0.12, y + s*0.18, x + s*0.88, y + s*0.82,
                            outline=color, width=width)
    # sun
    canvas.create_oval(x + s*0.28, y + s*0.30, x + s*0.42, y + s*0.44, outline=color, width=width)
    # mountain
    canvas.create_line(x + s*0.14, y + s*0.72, x + s*0.40, y + s*0.42,
                       x + s*0.58, y + s*0.62, x + s*0.72, y + s*0.48,
                       x + s*0.86, y + s*0.72, **k)


def icon_pin(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    cx = x + s * 0.5
    top = y + s * 0.16
    canvas.create_oval(x + s*0.20, top, x + s*0.80, top + s*0.50, outline=color, width=width)
    canvas.create_line(cx, top + s*0.48, cx, y + s*0.90, fill=color, width=width, capstyle="round")
    canvas.create_oval(cx - s*0.09, top + s*0.16, cx + s*0.09, top + s*0.34, outline=color, width=width)


def icon_brain(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    k = _stroke_kwargs(color, width)
    canvas.create_oval(x + s*0.16, y + s*0.18, x + s*0.56, y + s*0.58, outline=color, width=width)
    canvas.create_oval(x + s*0.44, y + s*0.18, x + s*0.84, y + s*0.58, outline=color, width=width)
    canvas.create_arc(x + s*0.20, y + s*0.42, x + s*0.60, y + s*0.86, start=180, extent=180,
                      style="arc", outline=color, width=width)
    canvas.create_arc(x + s*0.40, y + s*0.42, x + s*0.80, y + s*0.86, start=180, extent=180,
                      style="arc", outline=color, width=width)


def icon_camera(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_rectangle(x + s*0.12, y + s*0.30, x + s*0.88, y + s*0.82,
                            outline=color, width=width)
    canvas.create_polygon(x + s*0.32, y + s*0.30, x + s*0.40, y + s*0.18,
                         x + s*0.60, y + s*0.18, x + s*0.68, y + s*0.30,
                         outline=color, fill="", width=width, smooth=False)
    canvas.create_oval(x + s*0.38, y + s*0.44, x + s*0.62, y + s*0.68, outline=color, width=width)


def icon_shield(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    cx = x + s * 0.5
    canvas.create_polygon(
        cx, y + s*0.12,
        x + s*0.82, y + s*0.26,
        x + s*0.82, y + s*0.52,
        cx, y + s*0.90,
        x + s*0.18, y + s*0.52,
        x + s*0.18, y + s*0.26,
        outline=color, fill="", width=width, smooth=True, splinesteps=12,
    )
    canvas.create_line(x + s*0.36, y + s*0.48, x + s*0.46, y + s*0.60,
                       x + s*0.66, y + s*0.34, fill=color, width=width,
                       capstyle="round", joinstyle="round")


def icon_search(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_oval(x + s*0.16, y + s*0.16, x + s*0.62, y + s*0.62, outline=color, width=width)
    canvas.create_line(x + s*0.58, y + s*0.58, x + s*0.86, y + s*0.86, fill=color,
                       width=width, capstyle="round")


def icon_folder(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_polygon(
        x + s*0.12, y + s*0.28, x + s*0.38, y + s*0.28, x + s*0.46, y + s*0.38,
        x + s*0.88, y + s*0.38, x + s*0.88, y + s*0.80, x + s*0.12, y + s*0.80,
        outline=color, fill="", width=width, smooth=False,
    )


def icon_download(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    cx = x + s * 0.5
    canvas.create_line(cx, y + s*0.15, cx, y + s*0.58, fill=color, width=width, capstyle="round")
    canvas.create_line(x + s*0.30, y + s*0.42, cx, y + s*0.62, x + s*0.70, y + s*0.42,
                       fill=color, width=width, capstyle="round", joinstyle="round")
    canvas.create_line(x + s*0.16, y + s*0.78, x + s*0.84, y + s*0.78, fill=color,
                       width=width, capstyle="round")


def icon_refresh(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    cx, cy = x + s*0.5, y + s*0.5
    r = s * 0.32
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=30, extent=280,
                      style="arc", outline=color, width=width)
    ang = math.radians(30)
    ax, ay = cx + r * math.cos(ang), cy - r * math.sin(ang)
    canvas.create_polygon(ax, ay - s*0.08, ax + s*0.10, ay + s*0.02, ax - s*0.02, ay + s*0.10,
                         fill=color, outline=color)


def icon_close(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_line(x + s*0.24, y + s*0.24, x + s*0.76, y + s*0.76, fill=color,
                       width=width, capstyle="round")
    canvas.create_line(x + s*0.76, y + s*0.24, x + s*0.24, y + s*0.76, fill=color,
                       width=width, capstyle="round")


def icon_chevron_left(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_line(x + s*0.62, y + s*0.20, x + s*0.36, y + s*0.5, x + s*0.62, y + s*0.80,
                       fill=color, width=width, capstyle="round", joinstyle="round")


def icon_chevron_right(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_line(x + s*0.38, y + s*0.20, x + s*0.64, y + s*0.5, x + s*0.38, y + s*0.80,
                       fill=color, width=width, capstyle="round", joinstyle="round")


def icon_check(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_line(x + s*0.18, y + s*0.52, x + s*0.40, y + s*0.74, x + s*0.84, y + s*0.24,
                       fill=color, width=width, capstyle="round", joinstyle="round")


def icon_map(canvas: tk.Canvas, x, y, size, color="white", width=2.0):
    s = size
    canvas.create_polygon(
        x + s*0.14, y + s*0.22, x + s*0.40, y + s*0.14, x + s*0.60, y + s*0.22,
        x + s*0.86, y + s*0.14, x + s*0.86, y + s*0.78, x + s*0.60, y + s*0.86,
        x + s*0.40, y + s*0.78, x + s*0.14, y + s*0.86,
        outline=color, fill="", width=width, smooth=False,
    )
    canvas.create_line(x + s*0.40, y + s*0.14, x + s*0.40, y + s*0.78, fill=color, width=width)
    canvas.create_line(x + s*0.60, y + s*0.22, x + s*0.60, y + s*0.86, fill=color, width=width)


ICON_DRAW_FUNCS = {
    "image": icon_image,
    "pin": icon_pin,
    "brain": icon_brain,
    "camera": icon_camera,
    "shield": icon_shield,
    "search": icon_search,
    "folder": icon_folder,
    "download": icon_download,
    "refresh": icon_refresh,
    "close": icon_close,
    "chevron_left": icon_chevron_left,
    "chevron_right": icon_chevron_right,
    "check": icon_check,
    "map": icon_map,
}


def draw_icon(canvas: tk.Canvas, name: str, x, y, size, color="white", width=2.0):
    """Draws a named icon into an existing canvas at (x, y), size x size box."""
    fn = ICON_DRAW_FUNCS.get(name)
    if fn:
        fn(canvas, x, y, size, color=color, width=width)


def make_icon_canvas(parent, name: str, size: int, color="white", bg=None, width=2.0) -> tk.Canvas:
    """Convenience: a standalone Canvas widget sized exactly to the icon."""
    c = tk.Canvas(parent, width=size, height=size, bg=bg or parent.cget("bg"),
                 highlightthickness=0, bd=0)
    draw_icon(c, name, 0, 0, size, color=color, width=width)
    return c
