"""
Double-click detail modal for a single scanned image record — rebuilt to
match the target mockup layout:
  - image preview (top-left)
  - colorized profile pills (top-right): camera, resolution, GPS, C2PA validity
  - two side-by-side info cards: GPS Information / AI Probability
  - a tabbed panel below: EXIF | XMP | C2PA | Raw JSON
"""
from __future__ import annotations
import json
import os
import threading
import tkinter as tk
from tkinter import ttk

from raven_widgets import (
    BG, PANEL, PANEL2, PANEL_HOVER, BORDER, TEXT, SUBTLE,
    VERDICT_COLORS, TIER_COLORS, RADIUS,
    Pill, TabbedPanel, RoundedButton, RoundedFrame,
)
from raven_icons import make_icon_canvas

_geocode_cache: dict = {}


def _try_reverse_geocode(lat: float, lon: float) -> str | None:
    """
    Best-effort offline-safe reverse geocode using OpenStreetMap Nominatim.
    Returns None immediately (no exception, no hang) if there's no network or
    the request fails -- GPS coordinates are always shown regardless; this is
    purely a nice-to-have enrichment, same as the "Address" line in the mockup.
    """
    key = (round(lat, 5), round(lon, 5))
    if key in _geocode_cache:
        return _geocode_cache[key]
    try:
        import urllib.request
        url = (f"https://nominatim.openstreetmap.org/reverse?format=json"
               f"&lat={lat}&lon={lon}&zoom=14&addressdetails=0")
        req = urllib.request.Request(url, headers={"User-Agent": "RavenMetadataExtractor/2.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            address = data.get("display_name")
            _geocode_cache[key] = address
            return address
    except Exception:
        _geocode_cache[key] = None
        return None


class DetailModal(tk.Toplevel):
    def __init__(self, parent, record: dict, ui_font: str, mono_font: str):
        super().__init__(parent)
        self.record = record
        self.ui_font = ui_font
        self.mono_font = mono_font
        self._preview_imgtk = None  # keep a reference so Tk doesn't GC it

        file_info = record.get("file") or {}
        fname = file_info.get("filename", "Untitled")

        self.title(f"{fname} — Details")
        self.geometry("900x760")
        self.configure(bg=BG)
        self.minsize(720, 560)
        self.transient(parent)

        self._build(record)

        self.update_idletasks()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            w, h = 900, 760
            self.geometry(f"+{px + max(0, (pw - w)//2)}+{py + max(0, (ph - h)//2)}")
        except Exception:
            pass

        self.grab_set()

    # ------------------------------------------------------------------ build
    def _build(self, record: dict):
        meta = record.get("metadata") or {}
        file_info = record.get("file") or {}
        exif = meta.get("exif") or {}
        xmp = meta.get("xmp") or {}
        img_info = meta.get("image") or {}
        gps = meta.get("gps") or {}
        ai = meta.get("ai_indicators") or {}

        # ---- header bar (title + close) ------------------------------------
        header = tk.Frame(self, bg=PANEL, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"{file_info.get('filename', 'Untitled')} — Details",
                 bg=PANEL, fg=TEXT, font=(self.ui_font, 11, "bold")).pack(side="left", padx=16)
        close_icon = make_icon_canvas(header, "close", 16, color=SUBTLE, bg=PANEL)
        close_icon.pack(side="right", padx=16)
        close_icon.bind("<Button-1>", lambda e: self.destroy())
        close_icon.config(cursor="hand2")

        # scrollable body
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=880)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def _on_mousewheel(event):
            delta = -1 * (event.delta // 120) if event.delta else (1 if event.num == 5 else -1)
            canvas.yview_scroll(delta, "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        # ---- top row: preview (left) + pills (right) ------------------------
        top_row = tk.Frame(scroll_frame, bg=BG)
        top_row.pack(fill="x", padx=16, pady=(16, 8))

        preview_frame = RoundedFrame(top_row, bg_color=PANEL, radius=RADIUS,
                                     border_color=BORDER, width=230, height=230)
        preview_frame.pack(side="left", padx=(0, 16))
        self._render_preview(preview_frame.body, file_info.get("path"))

        pills_col = tk.Frame(top_row, bg=BG)
        pills_col.pack(side="left", fill="both", expand=True, anchor="n")
        self._render_pills_grid(pills_col, exif, img_info, gps, ai)

        # ---- side-by-side info cards: GPS | AI Probability ------------------
        cards_row = tk.Frame(scroll_frame, bg=BG)
        cards_row.pack(fill="x", padx=16, pady=(4, 8))
        gps_card = RoundedFrame(cards_row, bg_color=PANEL, radius=RADIUS, border_color=BORDER)
        gps_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ai_card = RoundedFrame(cards_row, bg_color=PANEL, radius=RADIUS, border_color=BORDER)
        ai_card.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self._render_gps_card(gps_card.body, gps)
        self._render_ai_card(ai_card.body, ai)

        # ---- tabbed panel: EXIF / XMP / C2PA / Raw JSON ----------------------
        tabs_frame = tk.Frame(scroll_frame, bg=BG)
        tabs_frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        tabbed = TabbedPanel(tabs_frame, self.ui_font)
        tabbed.pack(fill="both", expand=True)
        tabbed.add_tab("EXIF", lambda f: self._build_kv_tab(f, self._exif_rows(exif)))
        tabbed.add_tab("XMP", lambda f: self._build_kv_tab(
            f, [(k, str(v)) for k, v in xmp.items()] if xmp else [], empty="No XMP data in this image."))
        tabbed.add_tab("C2PA", lambda f: self._build_c2pa_tab(f, ai.get("c2pa") or {}))
        tabbed.add_tab("Raw JSON", lambda f: self._build_raw_json_tab(f, record))
        tabbed.show("EXIF")

        btn_row = tk.Frame(scroll_frame, bg=BG)
        btn_row.pack(fill="x", padx=16, pady=(0, 16))
        RoundedButton(btn_row, "Close", command=self.destroy, ui_font=self.ui_font,
                     bg_color=PANEL2, hover_color=PANEL_HOVER, fg=TEXT, size=9,
                     padx=16, pady=8).pack(side="right")

    # ------------------------------------------------------------------ preview
    def _render_preview(self, frame, path):
        placeholder = tk.Label(frame, text="No preview", bg=PANEL, fg=SUBTLE, font=(self.ui_font, 9))
        placeholder.pack(expand=True)
        if not path or not os.path.isfile(path):
            return
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((218, 218))
                self._preview_imgtk = ImageTk.PhotoImage(im)
            placeholder.destroy()
            tk.Label(frame, image=self._preview_imgtk, bg=PANEL).pack(expand=True)
        except Exception:
            placeholder.config(text="Preview unavailable\n(file moved or unreadable)")

    # ------------------------------------------------------------------ pills
    def _render_pills_grid(self, parent, exif, img_info, gps, ai):
        row1 = tk.Frame(parent, bg=BG)
        row1.pack(fill="x", pady=(0, 6))
        row2 = tk.Frame(parent, bg=BG)
        row2.pack(fill="x", pady=(0, 6))
        row3 = tk.Frame(parent, bg=BG)
        row3.pack(fill="x")

        cam = f"{exif.get('Make', '')} {exif.get('Model', '')}".strip()
        if cam:
            Pill(row1, cam, "#2e7d32", self.ui_font).pack(side="left", padx=(0, 6), pady=2)

        w, h = img_info.get("width"), img_info.get("height")
        if w and h:
            Pill(row1, f"{w} × {h}", "#1565c0", self.ui_font).pack(side="left", padx=(0, 6), pady=2)

        lat = (gps or {}).get("decimal", {}).get("latitude")
        if lat is not None:
            Pill(row2, "GPS", "#1565c0", self.ui_font).pack(side="left", padx=(0, 6), pady=2)

        if cam:
            Pill(row2, "Camera", "#2e7d32", self.ui_font).pack(side="left", padx=(0, 6), pady=2)

        c2pa = (ai or {}).get("c2pa") or {}
        if c2pa.get("present"):
            valid = c2pa.get("valid")
            label = "C2PA Valid" if valid else ("C2PA Present" if valid is None else "C2PA Invalid")
            color = "#6a1b9a" if valid else ("#5c6670" if valid is None else "#c0392b")
            Pill(row3, label, color, self.ui_font).pack(side="left", padx=(0, 6), pady=2)

    # ------------------------------------------------------------------ GPS card
    def _render_gps_card(self, card, gps):
        header_row = tk.Frame(card, bg=PANEL)
        header_row.pack(fill="x", padx=14, pady=(12, 8))
        icon_c = make_icon_canvas(header_row, "pin", 16, color=TEXT, bg=PANEL)
        icon_c.pack(side="left", padx=(0, 6))
        tk.Label(header_row, text="GPS Information", bg=PANEL, fg=TEXT,
                 font=(self.ui_font, 10, "bold"), anchor="w").pack(side="left")

        dec = (gps or {}).get("decimal") or {}
        lat, lon, alt = dec.get("latitude"), dec.get("longitude"), dec.get("altitude_m")

        if lat is None or lon is None:
            tk.Label(card, text="No GPS data in this image", bg=PANEL, fg=SUBTLE,
                     font=(self.ui_font, 9), anchor="w").pack(fill="x", padx=14, pady=(0, 14))
            return

        def row(label, value):
            r = tk.Frame(card, bg=PANEL)
            r.pack(fill="x", padx=14, pady=2)
            tk.Label(r, text=label, bg=PANEL, fg=SUBTLE, font=(self.ui_font, 8),
                     anchor="w").pack(anchor="w")
            tk.Label(r, text=value, bg=PANEL, fg=TEXT, font=(self.ui_font, 10, "bold"),
                     anchor="w", wraplength=340, justify="left").pack(anchor="w")

        row("Latitude", f"{lat:.6f}°")
        row("Longitude", f"{lon:.6f}°")
        if alt is not None:
            row("Altitude", f"{alt} m")

        addr_frame = tk.Frame(card, bg=PANEL)
        addr_frame.pack(fill="x", padx=14, pady=(4, 4))
        tk.Label(addr_frame, text="Address", bg=PANEL, fg=SUBTLE, font=(self.ui_font, 8),
                 anchor="w").pack(anchor="w")
        addr_lbl = tk.Label(addr_frame, text="Looking up… (needs network, skipped if offline)",
                            bg=PANEL, fg=TEXT, font=(self.ui_font, 9), anchor="w",
                            wraplength=340, justify="left")
        addr_lbl.pack(anchor="w")

        def _fill_address():
            addr = _try_reverse_geocode(lat, lon)
            try:
                addr_lbl.config(text=addr if addr else "Unavailable (offline or lookup failed)")
            except tk.TclError:
                pass
        threading.Thread(target=_fill_address, daemon=True).start()

        maps_url = dec.get("google_maps_url")
        if maps_url:
            link = tk.Label(card, text="Open in Maps ↗", bg=PANEL, fg="#4a90c2",
                            font=(self.ui_font, 9, "underline"), cursor="hand2", anchor="w")
            link.pack(anchor="w", padx=14, pady=(4, 14))
            link.bind("<Button-1>", lambda e: self._open_url(maps_url))
        else:
            tk.Frame(card, bg=PANEL, height=10).pack()

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    # ------------------------------------------------------------------ AI card
    def _render_ai_card(self, card, ai):
        header_row = tk.Frame(card, bg=PANEL)
        header_row.pack(fill="x", padx=14, pady=(12, 8))
        icon_c = make_icon_canvas(header_row, "brain", 16, color=TEXT, bg=PANEL)
        icon_c.pack(side="left", padx=(0, 6))
        tk.Label(header_row, text="AI Probability", bg=PANEL, fg=TEXT,
                 font=(self.ui_font, 10, "bold"), anchor="w").pack(side="left")

        if not ai:
            tk.Label(card, text="No AI analysis available.", bg=PANEL, fg=SUBTLE,
                     font=(self.ui_font, 9)).pack(anchor="w", padx=14, pady=(0, 14))
            return

        score = ai.get("suspicion_score", 0)
        confidence = ai.get("confidence", "low")
        conf_color = {"high": "#c0392b", "medium": "#d98324", "low": "#5c6670"}.get(confidence, "#5c6670")

        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x", padx=14)
        score_col = tk.Frame(top, bg=PANEL)
        score_col.pack(side="left")
        tk.Label(score_col, text="Score", bg=PANEL, fg=SUBTLE, font=(self.ui_font, 8),
                 anchor="w").pack(anchor="w")
        score_color = VERDICT_COLORS.get(ai.get("verdict"), "#5c6670")
        tk.Label(score_col, text=f"{score}%", bg=PANEL, fg=score_color,
                 font=(self.ui_font, 20, "bold")).pack(anchor="w")

        conf_col = tk.Frame(top, bg=PANEL)
        conf_col.pack(side="left", padx=(28, 0))
        tk.Label(conf_col, text="Confidence", bg=PANEL, fg=SUBTLE, font=(self.ui_font, 8),
                 anchor="w").pack(anchor="w")
        tk.Label(conf_col, text=confidence.capitalize(), bg=PANEL, fg=conf_color,
                 font=(self.ui_font, 12, "bold")).pack(anchor="w")

        # grouped signals by tier, matching mockup's Strong/Moderate/Weak groups
        signals = ai.get("signals", [])
        grouped: dict[str, list] = {"strong": [], "moderate": [], "weak": [], "info": []}
        for sig in signals:
            if isinstance(sig, dict):
                grouped.setdefault(sig.get("tier", "info"), []).append(sig.get("label", ""))
            else:
                grouped["info"].append(str(sig))

        sig_box = tk.Frame(card, bg=PANEL)
        sig_box.pack(fill="x", padx=14, pady=(10, 6))
        tier_titles = {"strong": "Strong", "moderate": "Moderate", "weak": "Weak", "info": "Info"}
        any_shown = False
        for tier in ("strong", "moderate", "weak", "info"):
            items = grouped.get(tier) or []
            if not items:
                continue
            any_shown = True
            tk.Label(sig_box, text=tier_titles[tier], bg=PANEL, fg=TIER_COLORS[tier],
                     font=(self.ui_font, 9, "bold"), anchor="w").pack(fill="x", pady=(6, 0))
            for label in items:
                row = tk.Frame(sig_box, bg=PANEL)
                row.pack(fill="x", padx=(6, 0))
                tk.Label(row, text="•", bg=PANEL, fg=TIER_COLORS[tier],
                         font=(self.ui_font, 9)).pack(side="left")
                tk.Label(row, text=label, bg=PANEL, fg=TEXT, font=(self.ui_font, 9),
                         anchor="w", wraplength=300, justify="left").pack(
                    side="left", fill="x", expand=True, padx=(4, 0))
        if not any_shown:
            tk.Label(sig_box, text="No indicators detected.", bg=PANEL, fg=SUBTLE,
                     font=(self.ui_font, 9)).pack(anchor="w")

        tk.Label(card, text=ai.get("disclaimer", ""), bg=PANEL, fg=SUBTLE,
                 font=(self.ui_font, 8, "italic"), wraplength=340,
                 justify="left").pack(fill="x", padx=14, pady=(4, 14))

    # ------------------------------------------------------------------ tabs
    def _exif_rows(self, exif: dict) -> list[tuple[str, str]]:
        # Curated common order first (matches mockup), then any remaining tags.
        preferred = ["Make", "Model", "LensModel", "DateTimeOriginal", "ExposureTime",
                    "FNumber", "ISOSpeedRatings", "FocalLength", "Flash", "WhiteBalance",
                    "MeteringMode", "ExposureProgram", "Software"]
        rows = []
        seen = set()
        for k in preferred:
            if k in exif and exif[k] not in (None, ""):
                rows.append((k, str(exif[k])))
                seen.add(k)
        for k, v in exif.items():
            if k not in seen and v not in (None, ""):
                rows.append((k, str(v)))
        return rows

    def _build_kv_tab(self, frame, rows, empty="No data available."):
        if not rows:
            tk.Label(frame, text=empty, bg=PANEL, fg=SUBTLE,
                     font=(self.ui_font, 9)).pack(anchor="w", padx=16, pady=16)
            return
        canvas = tk.Canvas(frame, bg=PANEL, highlightthickness=0, height=280)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=PANEL)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        header = tk.Frame(inner, bg=PANEL2)
        header.pack(fill="x")
        tk.Label(header, text="Tag", bg=PANEL2, fg=SUBTLE, font=(self.ui_font, 9, "bold"),
                 width=22, anchor="w").pack(side="left", padx=(12, 4), pady=6)
        tk.Label(header, text="Value", bg=PANEL2, fg=SUBTLE, font=(self.ui_font, 9, "bold"),
                 anchor="w").pack(side="left", padx=4, pady=6)

        for i, (k, v) in enumerate(rows):
            row_bg = PANEL if i % 2 == 0 else "#293039"
            r = tk.Frame(inner, bg=row_bg)
            r.pack(fill="x")
            tk.Label(r, text=k, bg=row_bg, fg=SUBTLE, font=(self.ui_font, 9),
                     width=22, anchor="w").pack(side="left", padx=(12, 4), pady=4)
            tk.Label(r, text=v, bg=row_bg, fg=TEXT, font=(self.ui_font, 9), anchor="w",
                     wraplength=520, justify="left").pack(side="left", fill="x", expand=True, padx=4, pady=4)

    def _build_c2pa_tab(self, frame, c2pa: dict):
        if not c2pa.get("available"):
            tk.Label(frame, text="c2pa-python not installed — C2PA manifest reading is an "
                                 "optional feature. See requirements-optional.txt.",
                     bg=PANEL, fg=SUBTLE, font=(self.ui_font, 9), wraplength=560,
                     justify="left").pack(anchor="w", padx=16, pady=16)
            return
        if not c2pa.get("present"):
            tk.Label(frame, text="No C2PA / Content Credentials manifest found in this image.",
                     bg=PANEL, fg=SUBTLE, font=(self.ui_font, 9)).pack(anchor="w", padx=16, pady=16)
            return

        rows = [
            ("Manifest present", "Yes"),
            ("Validation", {"True": "Valid", "False": "Invalid", "None": "Unknown"}.get(
                str(c2pa.get("valid")), "Unknown")),
            ("Claim generator", c2pa.get("claim_generator") or "—"),
            ("Software agent(s)", ", ".join(c2pa.get("software_agents", [])) or "—"),
            ("Digital source type(s)", "\n".join(c2pa.get("digital_source_types", [])) or "—"),
            ("AI-generated (per manifest)", {True: "Yes", False: "No", None: "Unresolved"}.get(
                c2pa.get("ai_generated"))),
        ]
        self._build_kv_tab(frame, rows)
        if c2pa.get("error"):
            tk.Label(frame, text=f"Note: {c2pa['error']}", bg=PANEL, fg="#d98324",
                     font=(self.ui_font, 8, "italic"), wraplength=560,
                     justify="left").pack(anchor="w", padx=16, pady=(0, 12))

    def _build_raw_json_tab(self, frame, record: dict):
        pretty = json.dumps(record, indent=2, ensure_ascii=False, default=str)
        text = tk.Text(frame, wrap="none", bg=PANEL, fg=TEXT, relief="flat",
                       font=(self.mono_font, 9), padx=10, pady=10, height=16)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        text.pack(side="top", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        text.insert("1.0", pretty)
        text.config(state="disabled")
