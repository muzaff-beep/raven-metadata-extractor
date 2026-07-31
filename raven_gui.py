#!/usr/bin/env python3
"""
Raven Metadata Extractor — GUI (Tkinter, stdlib only)

Layout follows the target design:
  - Scan tab: folder picker + live scrolling scan log (left column), dashboard
    cards + filter/search + paginated results table (right column). Double-
    click any row opens the tabbed detail modal.
  - History tab: every saved report, double-click to reload it into Scan.
"""
from __future__ import annotations
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from raven import (
    process_folder, build_summary, save_report,
    load_history, load_report, get_reports_dir,
)
from raven_widgets import (
    BG, PANEL, PANEL2, PANEL_HOVER, BORDER, TEXT, SUBTLE, ACCENT, ACCENT_HOVER,
    VERDICT_LABELS, RADIUS, RADIUS_BTN,
    DashboardCard, RoundedButton, RoundedFrame,
)
from raven_icons import make_icon_canvas

PAGE_SIZE = 10

# Drop a banner/logo image at this path (relative to this file's folder) to
# show it at the top of the app window. Recommended size: any width, height
# exactly 64px (it's scaled to this height automatically, keeping aspect
# ratio) -- PNG with transparency works well. If the file isn't present, a
# plain text banner is shown instead, so nothing breaks either way.
HEADER_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "header.png")
HEADER_HEIGHT = 64

# Window/taskbar icon shown in the title bar, Alt-Tab switcher, and taskbar.
# - Windows: prefers app_icon.ico (multi-resolution .ico is what Windows
#   actually wants for crisp taskbar/title-bar rendering); falls back to
#   app_icon.png via iconphoto if only a PNG is provided.
# - macOS/Linux: uses app_icon.png via iconphoto (Tk has no .icns support here;
#   for a proper Dock icon on macOS, also set it in the PyInstaller .spec via
#   the `icon=` argument pointing at an .icns file -- see build notes in
#   requirements-optional.txt / README).
# If none of these files exist, the app just uses Tk's default feather icon --
# nothing breaks either way.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
APP_ICON_ICO_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")
APP_ICON_PNG_PATH = os.path.join(ASSETS_DIR, "app_icon.png")


def _pick_font(*candidates: str) -> str:
    """Return the first font family from candidates that's actually installed;
    falls back to a generic Tk family name if none match."""
    try:
        import tkinter.font as tkfont
        available = set(tkfont.families())
    except Exception:
        return candidates[-1]
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


# Resolved lazily inside RavenApp.__init__ (after a Tk root exists) since
# tkinter.font.families() requires a live root window.
UI_FONT = "TkDefaultFont"
MONO_FONT = "TkFixedFont"


class RavenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        global UI_FONT, MONO_FONT
        UI_FONT = _pick_font("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu",
                             "DejaVu Sans", "Helvetica", "TkDefaultFont")
        MONO_FONT = _pick_font("Consolas", "SF Mono", "Menlo", "Ubuntu Mono",
                               "DejaVu Sans Mono", "Courier New", "TkFixedFont")
        self.title("Raven Metadata Extractor")
        self.geometry("1360x900")
        self.configure(bg=BG)
        self.minsize(1040, 680)

        self._set_app_icon()
        self._init_style()
        self._build_header()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.scan_tab = ScanTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)

        self.notebook.add(self.scan_tab, text="  Scan  ")
        self.notebook.add(self.history_tab, text="  History  ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _set_app_icon(self):
        """
        Sets the window/taskbar icon. Tries the platform-preferred format
        first, falls back to PNG via iconphoto, and silently does nothing if
        neither file is present -- Tk's default icon is used instead, the app
        never errors because an icon file hasn't been added yet.
        """
        self._app_icon_imgtk = None  # keep a reference so Tk doesn't GC it
        if os.name == "nt" and os.path.isfile(APP_ICON_ICO_PATH):
            try:
                self.iconbitmap(APP_ICON_ICO_PATH)
                return
            except Exception:
                pass  # fall through to PNG attempt below

        if os.path.isfile(APP_ICON_PNG_PATH):
            try:
                from PIL import Image, ImageTk
                with Image.open(APP_ICON_PNG_PATH) as im:
                    im = im.convert("RGBA")
                    self._app_icon_imgtk = ImageTk.PhotoImage(im)
                self.iconphoto(True, self._app_icon_imgtk)
            except Exception:
                pass  # keep Tk's default icon rather than error out

    def _build_header(self):
        """
        Graphical header banner at the top of the window.

        Drop an image at HEADER_IMAGE_PATH (see constant near the top of this
        file) and it's displayed here, scaled to fit the banner height while
        preserving aspect ratio. If the file isn't present, a plain colored
        bar with the app title is shown instead -- the app never breaks or
        shows an error just because the image hasn't been added yet.
        """
        self._header_imgtk = None  # keep a reference so Tk doesn't GC it
        self.header_frame = tk.Frame(self, bg=PANEL, height=HEADER_HEIGHT,
                                     highlightbackground=BORDER, highlightthickness=0)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        loaded = False
        if HEADER_IMAGE_PATH and os.path.isfile(HEADER_IMAGE_PATH):
            try:
                from PIL import Image, ImageTk
                with Image.open(HEADER_IMAGE_PATH) as im:
                    im = im.convert("RGBA")
                    ratio = HEADER_HEIGHT / im.height
                    new_w = max(1, int(im.width * ratio))
                    im = im.resize((new_w, HEADER_HEIGHT))
                    self._header_imgtk = ImageTk.PhotoImage(im)
                tk.Label(self.header_frame, image=self._header_imgtk, bg=PANEL).pack(
                    side="left", fill="y")
                loaded = True
            except Exception:
                loaded = False

        if not loaded:
            # Fallback: plain text banner, same spot the image would occupy.
            tk.Label(self.header_frame, text="Raven Metadata Extractor", bg=PANEL, fg=TEXT,
                     font=(UI_FONT, 15, "bold")).pack(side="left", padx=20)

    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT,
                        padding=(18, 8), font=(UI_FONT, 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=(UI_FONT, 10))
        style.configure("Head.TLabel", background=BG, foreground=TEXT, font=(UI_FONT, 14, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=SUBTLE, font=(UI_FONT, 9))
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=30, font=(UI_FONT, 9), borderwidth=0)
        style.configure("Treeview.Heading", background=BG, foreground=SUBTLE, font=(UI_FONT, 9, "bold"))
        style.map("Treeview", background=[("selected", "#33404a")])
        style.configure("Green.TButton", background=ACCENT, foreground="white",
                        font=(UI_FONT, 11, "bold"), padding=8)
        style.map("Green.TButton", background=[("active", "#256628")])
        style.configure("TButton", padding=6)
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG)

    def _on_tab_change(self, _event):
        current = self.notebook.tab(self.notebook.select(), "text").strip()
        if current == "History":
            self.history_tab.refresh()


# ---------------------------------------------------------------- Scan tab
class ScanTab(ttk.Frame):
    """
    Combined scan + results screen, matching the mockup: folder picker + live
    console on the left, dashboard cards + filter/search + paginated table on
    the right. Double-click any row opens the detail modal.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.folder = tk.StringVar()
        self.recursive = tk.BooleanVar(value=True)
        self.records: list[dict] = []
        self.filtered: list[dict] = []
        self.summary: dict | None = None
        self.current_page = 1
        self.filter_choice = tk.StringVar(value="All Images")
        self.search_var = tk.StringVar()
        self._log_queue: list[str] = []
        self._scanning = False

        root_row = tk.Frame(self, bg=BG)
        root_row.pack(fill="both", expand=True, padx=14, pady=14)
        root_row.columnconfigure(0, weight=0, minsize=330)
        root_row.columnconfigure(1, weight=1)
        root_row.rowconfigure(0, weight=1)

        left = tk.Frame(root_row, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = tk.Frame(root_row, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

        self.search_var.trace_add("write", lambda *_: self._on_filter_change())

    # ================================================================ LEFT
    def _build_left(self, parent):
        tk.Label(parent, text="Scan a Folder", bg=BG, fg=TEXT,
                 font=(UI_FONT, 14, "bold"), anchor="w").pack(fill="x")
        tk.Label(parent, text="Extracts EXIF / GPS / XMP + AI-generation indicators",
                 bg=BG, fg=SUBTLE, font=(UI_FONT, 9), anchor="w",
                 wraplength=310, justify="left").pack(fill="x", pady=(2, 12))

        tk.Label(parent, text="Folder:", bg=BG, fg=SUBTLE, font=(UI_FONT, 9),
                 anchor="w").pack(fill="x")
        row_wrap = RoundedFrame(parent, bg_color=PANEL, radius=RADIUS_BTN, border_color=BORDER, height=38)
        row_wrap.pack(fill="x", pady=(2, 8))
        row = row_wrap.body
        entry = tk.Entry(row, textvariable=self.folder, font=(UI_FONT, 9),
                         bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0)
        entry.pack(side="left", fill="both", expand=True, ipady=8, padx=(10, 4), pady=2)
        browse_btn = RoundedButton(row, "Browse", command=self.browse, ui_font=UI_FONT,
                                   bg_color=PANEL2, hover_color=PANEL_HOVER, fg=TEXT,
                                   size=9, padx=12, pady=6, icon="folder")
        browse_btn.pack(side="right", padx=(0, 4), pady=4)

        ttk.Checkbutton(parent, text="Scan subfolders",
                        variable=self.recursive).pack(anchor="w", pady=(2, 12))

        self.run_btn = RoundedButton(parent, "Start Scan", command=self.run, ui_font=UI_FONT,
                                     bg_color=ACCENT, hover_color=ACCENT_HOVER, fg="white",
                                     size=11, padx=18, pady=11, icon="check")
        self.run_btn.pack(fill="x", pady=(0, 14))

        # ---- Status box -----------------------------------------------------
        status_box = RoundedFrame(parent, bg_color=PANEL, radius=RADIUS, border_color=BORDER)
        status_box.pack(fill="x", pady=(0, 14))
        sb = status_box.body
        tk.Label(sb, text="Status", bg=PANEL, fg=TEXT, font=(UI_FONT, 10, "bold"),
                 anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        self.status_var = tk.StringVar(value="Idle")
        tk.Label(sb, textvariable=self.status_var, bg=PANEL, fg=ACCENT,
                 font=(UI_FONT, 10, "bold"), anchor="w").pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(sb, text="Reports are saved to:", bg=PANEL, fg=SUBTLE,
                 font=(UI_FONT, 8), anchor="w").pack(fill="x", padx=14)
        path_row = tk.Frame(sb, bg=PANEL)
        path_row.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(path_row, text=str(get_reports_dir()), bg=PANEL, fg="#4d9fd6",
                 font=(UI_FONT, 8, "underline"), anchor="w", wraplength=250,
                 justify="left", cursor="hand2").pack(side="left", fill="x", expand=True)
        folder_icon_btn = make_icon_canvas(path_row, "folder", 18, color=SUBTLE, bg=PANEL)
        folder_icon_btn.pack(side="right")
        folder_icon_btn.bind("<Button-1>", lambda e: self.open_reports_folder())
        folder_icon_btn.config(cursor="hand2")

        status_box.after_idle(lambda: status_box.configure(height=sb.winfo_reqheight() + 4))

        # ---- Live scan output -------------------------------------------------
        tk.Label(parent, text="Live Scan Output", bg=BG, fg=TEXT,
                 font=(UI_FONT, 10, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        console_wrap = RoundedFrame(parent, bg_color="#14171a", radius=RADIUS, border_color=BORDER)
        console_wrap.pack(fill="both", expand=True)
        console_frame = console_wrap.body
        self.console = tk.Text(console_frame, bg="#14171a", fg="#8fd694", relief="flat",
                               font=(MONO_FONT, 8),
                               padx=10, pady=8, wrap="word", state="disabled", bd=0,
                               highlightthickness=0)
        console_sb = ttk.Scrollbar(console_frame, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=console_sb.set)
        self.console.pack(side="left", fill="both", expand=True)
        console_sb.pack(side="right", fill="y")

        bottom_bar = tk.Frame(parent, bg=BG)
        bottom_bar.pack(fill="x", pady=(6, 0))
        self.footer_status = tk.StringVar(value="Ready")
        tk.Label(bottom_bar, textvariable=self.footer_status, bg=BG, fg=SUBTLE,
                 font=(UI_FONT, 8), anchor="w").pack(side="left")

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        try:
            self.console.config(state="normal")
            self.console.insert("end", line)
            self.console.see("end")
            self.console.config(state="disabled")
        except tk.TclError:
            pass

    def _clear_log(self):
        self.console.config(state="normal")
        self.console.delete("1.0", "end")
        self.console.config(state="disabled")

    def browse(self):
        folder = filedialog.askdirectory(title="Select folder containing images")
        if folder:
            self.folder.set(folder)

    def open_reports_folder(self):
        path = str(get_reports_dir())
        try:
            if os.name == "nt":
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except Exception:
            messagebox.showinfo("Reports folder", path)

    def run(self):
        if self._scanning:
            return
        folder = self.folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder", "Please choose a valid folder first.")
            return
        self._scanning = True
        self.run_btn.set_enabled(False)
        self.run_btn.set_text("Scanning…")
        self.status_var.set("Processing…")
        self.footer_status.set("Scanning…")
        self._clear_log()
        self._log(f"Starting scan…")
        self._log(f"Folder: {folder}")
        self._log(f"Recursive: {'Yes' if self.recursive.get() else 'No'}")
        self._log("-" * 40)
        threading.Thread(target=self._worker, args=(folder,), daemon=True).start()

    def _worker(self, folder):
        def on_progress(i, total, path, record):
            fname = os.path.basename(path)
            self.after(0, self._log, f"[{i}/{total}] {fname}")
            errs = record.get("errors") or []
            if errs:
                self.after(0, self._log, f"   ⚠ {errs[0]}")
            ai = (record.get("metadata") or {}).get("ai_indicators") or {}
            verdict = ai.get("verdict")
            if verdict in ("likely_ai", "possibly_ai"):
                label = VERDICT_LABELS.get(verdict, verdict)
                self.after(0, self._log, f"   → {label} ({ai.get('suspicion_score', 0)}%)")

        try:
            records = process_folder(folder, recursive=self.recursive.get(), on_progress=on_progress)
            summary = build_summary(records, folder)
            entry = save_report(records, summary, folder)
        except Exception as e:
            self.after(0, self._error, str(e))
            return
        self.after(0, self._done, entry, records, summary)

    def _done(self, entry, records, summary):
        self._scanning = False
        self.run_btn.set_enabled(True)
        self.run_btn.set_text("Start Scan")
        n = summary["totals"]["images_scanned"]
        self.records = records
        self.summary = summary
        self.current_page = 1
        self._log("-" * 40)
        self._log(f"Done. {n} image(s) scanned. Report saved: {entry['report_name']}")
        self.status_var.set(f"Done — {n} image(s)")
        self.footer_status.set(f"{n} images processed  •  Report: {entry['report_name']}")
        self._apply_filter()
        self._render_dashboard()
        if n == 0:
            messagebox.showinfo("No images", "No supported image files were found in that folder.")

    def _error(self, msg):
        self._scanning = False
        self.run_btn.set_enabled(True)
        self.run_btn.set_text("Start Scan")
        self.status_var.set("Error")
        self.footer_status.set(f"Error: {msg}")
        self._log(f"ERROR: {msg}")
        messagebox.showerror("Scan failed", msg)

    # ================================================================ RIGHT
    def _build_right(self, parent):
        self.dashboard_row = tk.Frame(parent, bg=BG)
        self.dashboard_row.pack(fill="x", pady=(0, 12))
        self._render_dashboard()  # renders placeholder cards (all zero) initially

        toolbar = tk.Frame(parent, bg=BG)
        toolbar.pack(fill="x", pady=(0, 8))

        filter_menu = tk.OptionMenu(toolbar, self.filter_choice,
                                    "All Images", "Likely AI", "Possibly AI", "Camera",
                                    "Has GPS", "No GPS", "Has C2PA",
                                    command=lambda *_: self._on_filter_change())
        filter_menu.config(bg=PANEL, fg=TEXT, bd=0, highlightthickness=0,
                           font=(UI_FONT, 9), activebackground=PANEL2, cursor="hand2")
        filter_menu["menu"].config(bg=PANEL, fg=TEXT)
        filter_menu.pack(side="left", padx=(0, 8), ipady=3)

        search_frame = RoundedFrame(toolbar, bg_color=PANEL, radius=RADIUS_BTN, border_color=BORDER, height=34)
        search_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        sf = search_frame.body
        search_icon = make_icon_canvas(sf, "search", 15, color=SUBTLE, bg=PANEL)
        search_icon.pack(side="left", padx=(10, 4))
        search_entry = tk.Entry(sf, textvariable=self.search_var, bg=PANEL, fg=TEXT,
                               insertbackground=TEXT, relief="flat", font=(UI_FONT, 9), bd=0)
        search_entry.pack(side="left", fill="both", expand=True, ipady=6, padx=(0, 10), pady=2)

        RoundedButton(toolbar, "Export Report", command=self._export_report_menu, ui_font=UI_FONT,
                     bg_color=PANEL2, hover_color=PANEL_HOVER, fg=TEXT, size=9,
                     padx=12, pady=7, icon="download").pack(side="left", padx=(0, 6))
        refresh_btn = RoundedButton(toolbar, "", command=self._refresh_current, ui_font=UI_FONT,
                                    bg_color=PANEL2, hover_color=PANEL_HOVER, fg=TEXT, size=9,
                                    padx=8, pady=7, icon="refresh")
        refresh_btn.pack(side="left")

        # ---- table -----------------------------------------------------------
        table_frame = tk.Frame(parent, bg=BG)
        table_frame.pack(fill="both", expand=True)

        cols = ("thumb", "file", "camera", "resolution", "date", "verdict", "gps", "c2pa")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        headers = [("thumb", "", 40), ("file", "Filename", 190), ("camera", "Camera", 130),
                  ("resolution", "Resolution", 100), ("date", "Date Taken", 140),
                  ("verdict", "AI Verdict", 110), ("gps", "GPS", 50), ("c2pa", "C2PA", 60)]
        for c, txt, w in headers:
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="w", minwidth=40)
        tree_sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._open_modal_from_tree)

        self.tree.tag_configure("likely_ai", foreground="#e57373")
        self.tree.tag_configure("possibly_ai", foreground="#f0a860")
        self.tree.tag_configure("likely_camera", foreground="#81c784")
        self.tree.tag_configure("inconclusive", foreground=SUBTLE)

        # ---- pagination --------------------------------------------------------
        pager = tk.Frame(parent, bg=BG)
        pager.pack(fill="x", pady=(8, 0))
        self.pager_label = tk.Label(pager, text="No results", bg=BG, fg=SUBTLE, font=(UI_FONT, 9))
        self.pager_label.pack(side="left")
        pager_btns = tk.Frame(pager, bg=BG)
        pager_btns.pack(side="right")
        self.pager_btns_frame = pager_btns

    def _render_dashboard(self):
        for w in self.dashboard_row.winfo_children():
            w.destroy()

        s = self.summary or {}
        t = s.get("totals", {})
        ai = s.get("ai_indicators", {})
        c2pa_count = sum(1 for r in self.records
                         if ((r.get("metadata") or {}).get("ai_indicators") or {}).get("c2pa", {}).get("present"))

        cards = [
            ("image", "#1565c0", str(t.get("images_scanned", 0)), "Images", "Total analyzed"),
            ("pin", "#2e7d32", str(t.get("with_gps", 0)), "GPS", "With location"),
            ("brain", "#c0392b", str(ai.get("likely_ai_count", 0) + ai.get("possibly_ai_count", 0)), "AI Flags", "Potentially AI"),
            ("camera", "#6a1b9a", str(t.get("unique_cameras", 0)), "Cameras", "Unique models"),
            ("shield", "#1565c0", str(c2pa_count), "C2PA", "With credentials"),
        ]
        for icon, color, value, label, sub in cards:
            card = DashboardCard(self.dashboard_row, icon, color, value, label, UI_FONT, sub=sub)
            card.pack(side="left", fill="both", expand=True, padx=4)

    def _export_report_menu(self):
        if not self.summary:
            messagebox.showinfo("Nothing to export", "Run a scan first.")
            return
        messagebox.showinfo(
            "Export Report",
            f"The current report is already saved as JSON at:\n\n{get_reports_dir()}\n\n"
            "Open it from the History tab, or copy the file directly."
        )

    def _refresh_current(self):
        self._apply_filter()

    # ---- filtering / pagination -------------------------------------------
    def _on_filter_change(self):
        self.current_page = 1
        self._apply_filter()

    def _matches_filter(self, rec: dict) -> bool:
        choice = self.filter_choice.get()
        meta = rec.get("metadata") or {}
        ai = meta.get("ai_indicators") or {}
        gps = meta.get("gps") or {}
        has_gps = (gps.get("decimal") or {}).get("latitude") is not None
        verdict = ai.get("verdict")

        if choice == "Likely AI" and verdict != "likely_ai":
            return False
        if choice == "Possibly AI" and verdict != "possibly_ai":
            return False
        if choice == "Camera" and verdict != "likely_camera":
            return False
        if choice == "Has GPS" and not has_gps:
            return False
        if choice == "No GPS" and has_gps:
            return False
        if choice == "Has C2PA" and not (ai.get("c2pa") or {}).get("present"):
            return False

        q = self.search_var.get().strip().lower()
        if q:
            ex = meta.get("exif") or {}
            fname = (rec.get("file") or {}).get("filename", "")
            hay = f"{fname} {ex.get('Make','')} {ex.get('Model','')} {ex.get('LensModel','')} {verdict or ''}".lower()
            if q not in hay:
                return False
        return True

    def _apply_filter(self):
        self.filtered = [r for r in self.records if self._matches_filter(r)]
        self._render_page()

    def _total_pages(self) -> int:
        return max(1, (len(self.filtered) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _render_page(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        total_pages = self._total_pages()
        self.current_page = min(max(1, self.current_page), total_pages)
        start = (self.current_page - 1) * PAGE_SIZE
        page_items = self.filtered[start:start + PAGE_SIZE]

        for rec in page_items:
            meta = rec.get("metadata") or {}
            ex = meta.get("exif") or {}
            img = meta.get("image") or {}
            fname = (rec.get("file") or {}).get("filename", "?")
            cam = f"{ex.get('Make','')} {ex.get('Model','')}".strip() or "—"
            dt = str(ex.get("DateTimeOriginal", "") or "—")[:19]
            res = f"{img.get('width','?')}x{img.get('height','?')}" if img.get("width") else "—"
            gps_ok = "✓" if (meta.get("gps") or {}).get("decimal", {}).get("latitude") is not None else ""
            ai = meta.get("ai_indicators") or {}
            verdict = ai.get("verdict", "inconclusive")
            verdict_label = VERDICT_LABELS.get(verdict, verdict)
            c2pa_ok = "✓" if (ai.get("c2pa") or {}).get("present") else ""
            self.tree.insert("", "end", values=("", fname, cam, res, dt, verdict_label, gps_ok, c2pa_ok),
                            tags=(verdict,))

        n = len(self.filtered)
        if n == 0:
            self.pager_label.config(text="No results")
        else:
            end = min(start + PAGE_SIZE, n)
            self.pager_label.config(text=f"Showing {start + 1} to {end} of {n} images")
        self._render_pager(total_pages)

    def _render_pager(self, total_pages: int):
        for w in self.pager_btns_frame.winfo_children():
            w.destroy()

        def make_btn(text, page, enabled=True, active=False):
            b = RoundedButton(self.pager_btns_frame, text,
                             command=(lambda p=page: self._goto_page(p)) if enabled else None,
                             ui_font=UI_FONT, bg_color=(ACCENT if active else PANEL2),
                             hover_color=(ACCENT_HOVER if active else PANEL_HOVER),
                             fg=("white" if active else TEXT), size=9, padx=10, pady=5,
                             bold=active, radius=7)
            if not enabled:
                b.set_enabled(False)
            b.pack(side="left", padx=2)
            return b

        make_btn("«", 1, enabled=self.current_page > 1)
        make_btn("‹", self.current_page - 1, enabled=self.current_page > 1)

        # windowed page numbers around current page (max 5 visible)
        window = 2
        lo = max(1, self.current_page - window)
        hi = min(total_pages, self.current_page + window)
        if lo > 1:
            make_btn("1", 1)
            if lo > 2:
                tk.Label(self.pager_btns_frame, text="…", bg=BG, fg=SUBTLE).pack(side="left", padx=2)
        for p in range(lo, hi + 1):
            make_btn(str(p), p, active=(p == self.current_page))
        if hi < total_pages:
            if hi < total_pages - 1:
                tk.Label(self.pager_btns_frame, text="…", bg=BG, fg=SUBTLE).pack(side="left", padx=2)
            make_btn(str(total_pages), total_pages)

        make_btn("›", self.current_page + 1, enabled=self.current_page < total_pages)
        make_btn("»", total_pages, enabled=self.current_page < total_pages)

    def _goto_page(self, page: int):
        self.current_page = page
        self._render_page()

    # ---- modal -------------------------------------------------------------
    def _open_modal_from_tree(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        start = (self.current_page - 1) * PAGE_SIZE
        page_items = self.filtered[start:start + PAGE_SIZE]
        if idx >= len(page_items):
            return
        self._open_modal(page_items[idx])

    def _open_modal(self, record: dict):
        from raven_detail_modal import DetailModal
        DetailModal(self.app, record, UI_FONT, MONO_FONT)

    # ---- loading a saved report from History --------------------------------
    def load_report_data(self, records: list[dict], summary: dict | None, report_name: str = ""):
        self.records = records
        self.summary = summary
        self.current_page = 1
        self._render_dashboard()
        self._apply_filter()
        self.status_var.set(f"Loaded — {len(records)} image(s)")
        self.footer_status.set(f"Loaded report: {report_name}" if report_name else "Report loaded")
        self._clear_log()
        self._log(f"Loaded saved report: {report_name}" if report_name else "Loaded saved report")


# ---------------------------------------------------------------- History tab
class HistoryTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(20, 8))
        ttk.Label(header, text="Report History", style="Head.TLabel").pack(side="left")
        RoundedButton(header, "Open Reports Folder", command=self.open_folder, ui_font=UI_FONT,
                     bg_color=PANEL2, hover_color=PANEL_HOVER, fg=TEXT, size=9,
                     padx=12, pady=7, icon="folder").pack(side="right", padx=(6, 0))
        RoundedButton(header, "Refresh", command=self.refresh, ui_font=UI_FONT,
                     bg_color=PANEL2, hover_color=PANEL_HOVER, fg=TEXT, size=9,
                     padx=12, pady=7, icon="refresh").pack(side="right")

        cols = ("name", "source", "location", "timestamp", "count")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for c, txt, w in [("name", "Report Name", 260), ("source", "Source Folder", 160),
                          ("location", "Target Location", 300), ("timestamp", "Date / Time", 150),
                          ("count", "Images", 70)]:
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=20, pady=8)
        self.tree.bind("<Double-1>", self.open_selected)

        ttk.Label(self, text="Double-click a report to load it into the Scan tab.",
                  style="Sub.TLabel").pack(anchor="w", padx=20, pady=(0, 16))

        self._entries = []
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._entries = load_history()
        for e in self._entries:
            self.tree.insert("", "end", values=(
                e.get("report_name", "?"),
                e.get("source_folder_name", "?"),
                e.get("source_folder", "?"),
                e.get("timestamp", "?").replace("T", "  "),
                e.get("image_count", "?"),
            ))

    def open_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        entry = self._entries[idx]
        data = load_report(entry["report_path"])
        if not data:
            messagebox.showerror("Load failed", "Could not read that report file.")
            return
        if isinstance(data, list):
            records, summary = data, None
        else:
            records, summary = data.get("records", []), data.get("summary")
        self.app.scan_tab.load_report_data(records, summary, entry.get("report_name", ""))
        self.app.notebook.select(self.app.scan_tab)

    def open_folder(self):
        path = str(get_reports_dir())
        try:
            if os.name == "nt":
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except Exception:
            messagebox.showinfo("Reports folder", path)


if __name__ == "__main__":
    app = RavenApp()
    app.mainloop()
