#!/usr/bin/env python3
"""
Raven Metadata Extractor — GUI (Tkinter, stdlib only)

Tabs:
  1. Scan     — pick a folder, extract, auto-save timestamped report to RavenReports/
  2. History  — list of all saved reports (name, source folder, timestamp, count)
  3. Reader   — open any report: dashboard summary + image table + per-image drilldown
"""
from __future__ import annotations
import json
import os
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from raven import (
    process_folder, build_summary, save_report,
    load_history, load_report, get_reports_dir,
)

BG = "#1e2327"
PANEL = "#2a3138"
ACCENT = "#2e7d32"
TEXT = "#e6e6e6"
SUBTLE = "#9aa4ad"


class RavenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Raven Metadata Extractor")
        self.geometry("980x680")
        self.configure(bg=BG)
        self.minsize(880, 600)

        self._init_style()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.scan_tab = ScanTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)
        self.reader_tab = ReaderTab(self.notebook, self)

        self.notebook.add(self.scan_tab, text="  Scan  ")
        self.notebook.add(self.history_tab, text="  History  ")
        self.notebook.add(self.reader_tab, text="  Reader  ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT,
                        padding=(18, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Head.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 15, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=SUBTLE, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("CardBig.TLabel", background=PANEL, foreground="white", font=("Segoe UI", 20, "bold"))
        style.configure("CardLbl.TLabel", background=PANEL, foreground=SUBTLE, font=("Segoe UI", 9))
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=BG, foreground=TEXT, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT)])
        style.configure("Green.TButton", background=ACCENT, foreground="white",
                        font=("Segoe UI", 11, "bold"), padding=8)
        style.map("Green.TButton", background=[("active", "#256628")])
        style.configure("TButton", padding=6)

    def _on_tab_change(self, _event):
        current = self.notebook.tab(self.notebook.select(), "text").strip()
        if current == "History":
            self.history_tab.refresh()


# ---------------------------------------------------------------- Scan tab
class ScanTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.folder = tk.StringVar()
        self.recursive = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value=f"Reports are saved to: {get_reports_dir()}")

        ttk.Label(self, text="Scan a Folder", style="Head.TLabel").pack(anchor="w", padx=20, pady=(20, 2))
        ttk.Label(self, text="Extracts EXIF / GPS / XMP + AI-generation indicators, then saves a timestamped JSON report.",
                  style="Sub.TLabel").pack(anchor="w", padx=20, pady=(0, 16))

        row = ttk.Frame(self)
        row.pack(fill="x", padx=20, pady=6)
        entry = tk.Entry(row, textvariable=self.folder, font=("Segoe UI", 10),
                         bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        ttk.Button(row, text="Browse…", command=self.browse).pack(side="left")

        ttk.Checkbutton(self, text="Include subfolders (recursive)",
                        variable=self.recursive).pack(anchor="w", padx=20, pady=6)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=(14, 8))

        self.run_btn = ttk.Button(self, text="Extract Metadata", style="Green.TButton",
                                   command=self.run)
        self.run_btn.pack(fill="x", padx=20, pady=8)

        ttk.Label(self, textvariable=self.status, style="Sub.TLabel",
                  wraplength=900, justify="left").pack(anchor="w", padx=20, pady=(10, 16))

    def browse(self):
        folder = filedialog.askdirectory(title="Select folder containing images")
        if folder:
            self.folder.set(folder)

    def run(self):
        folder = self.folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder", "Please choose a valid folder first.")
            return
        self.run_btn.config(state="disabled")
        self.progress.start(12)
        self.status.set("Processing… extracting metadata and running AI indicators.")
        threading.Thread(target=self._worker, args=(folder,), daemon=True).start()

    def _worker(self, folder):
        try:
            records = process_folder(folder, recursive=self.recursive.get())
            summary = build_summary(records, folder)
            entry = save_report(records, summary, folder)
        except Exception as e:
            self.after(0, self._error, str(e))
            return
        self.after(0, self._done, entry, records, summary)

    def _done(self, entry, records, summary):
        self.progress.stop()
        self.run_btn.config(state="normal")
        n = summary["totals"]["images_scanned"]
        if n == 0:
            self.status.set("No supported image files found in that folder.")
            messagebox.showinfo("No images", "No supported image files were found.")
            return
        ai = summary["ai_indicators"]
        self.status.set(
            f"Done. {n} image(s) scanned. Saved report: {entry['report_name']}\n"
            f"Location: {entry['report_path']}\n"
            f"AI indicators: {ai['likely_ai_count']} likely, {ai['possibly_ai_count']} possibly AI-generated."
        )
        if messagebox.askyesno("Scan complete",
                               f"Scanned {n} image(s).\nSaved: {entry['report_name']}\n\nOpen it in the Reader now?"):
            self.app.reader_tab.load_from_path(entry["report_path"])
            self.app.notebook.select(self.app.reader_tab)

    def _error(self, msg):
        self.progress.stop()
        self.run_btn.config(state="normal")
        self.status.set(f"Error: {msg}")
        messagebox.showerror("Extraction failed", msg)


# ---------------------------------------------------------------- History tab
class HistoryTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(20, 8))
        ttk.Label(header, text="Report History", style="Head.TLabel").pack(side="left")
        ttk.Button(header, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(header, text="Open Reports Folder", command=self.open_folder).pack(side="right", padx=6)

        cols = ("name", "source", "location", "timestamp", "count")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for c, txt, w in [("name", "Report Name", 240), ("source", "Source Folder", 150),
                          ("location", "Target Location", 260), ("timestamp", "Date / Time", 150),
                          ("count", "Images", 70)]:
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=20, pady=8)
        self.tree.bind("<Double-1>", self.open_selected)

        ttk.Label(self, text="Double-click a report to open it in the Reader.",
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
        self.app.reader_tab.load_from_path(entry["report_path"])
        self.app.notebook.select(self.app.reader_tab)

    def open_folder(self):
        path = str(get_reports_dir())
        try:
            if os.name == "nt":
                os.startfile(path)  # noqa
            else:
                webbrowser.open(f"file://{path}")
        except Exception:
            messagebox.showinfo("Reports folder", path)


# ---------------------------------------------------------------- Reader tab
class ReaderTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.report = None
        self.records = []
        self.filtered = []

        top = ttk.Frame(self)
        top.pack(fill="x", padx=20, pady=(20, 8))
        ttk.Label(top, text="Report Reader", style="Head.TLabel").pack(side="left")
        ttk.Button(top, text="Open Report File…", command=self.open_file).pack(side="right")

        self.empty_lbl = ttk.Label(
            self, text="No report loaded. Open one from History, or click 'Open Report File…'.",
            style="Sub.TLabel")
        self.empty_lbl.pack(anchor="w", padx=20, pady=10)

        # dashboard cards
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x", padx=16, pady=6)

        # search
        self.search_row = ttk.Frame(self)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())

        # table + detail split
        self.split = ttk.Frame(self)

        left = ttk.Frame(self.split)
        left.pack(side="left", fill="both", expand=True)
        cols = ("file", "camera", "datetime", "resolution", "gps", "ai")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, txt, w in [("file", "File", 180), ("camera", "Camera", 130), ("datetime", "Date", 130),
                          ("resolution", "Resolution", 90), ("gps", "GPS", 50), ("ai", "AI?", 90)]:
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._show_detail)

        right = ttk.Frame(self.split, style="Panel.TFrame", width=340)
        right.pack(side="right", fill="both")
        right.pack_propagate(False)
        self.detail = tk.Text(right, wrap="word", bg=PANEL, fg=TEXT, relief="flat",
                              font=("Consolas", 9), padx=10, pady=10)
        self.detail.pack(fill="both", expand=True)
        self.detail.insert("1.0", "Select an image to see full metadata.")
        self.detail.config(state="disabled")

    # ---- loading
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open Raven report", initialdir=str(get_reports_dir()),
            filetypes=[("JSON reports", "*.json")])
        if path:
            self.load_from_path(path)

    def load_from_path(self, path):
        data = load_report(path)
        if not data:
            messagebox.showerror("Load failed", "Could not read that report file.")
            return
        # Support both new {summary, records} and legacy [records] shapes
        if isinstance(data, list):
            self.report = {"summary": None, "records": data}
        else:
            self.report = data
        self.records = self.report.get("records", [])
        self.filtered = list(self.records)
        self._render()

    # ---- rendering
    def _render(self):
        self.empty_lbl.pack_forget()
        summary = self.report.get("summary")

        for w in self.cards.winfo_children():
            w.destroy()
        if summary:
            self._render_cards(summary)

        if not self.search_row.winfo_ismapped():
            self.search_row.pack(fill="x", padx=20, pady=(10, 4))
            ttk.Label(self.search_row, text="Filter:").pack(side="left")
            ent = tk.Entry(self.search_row, textvariable=self.search_var, bg=PANEL, fg=TEXT,
                           insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
            ent.pack(side="left", fill="x", expand=True, ipady=4, padx=8)
        self.split.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        self._populate_table()

    def _render_cards(self, summary):
        t = summary.get("totals", {})
        ai = summary.get("ai_indicators", {})
        dr = summary.get("date_range") or {}
        sz = summary.get("size_stats") or {}
        cams = summary.get("camera_breakdown", [])
        top_cam = cams[0]["camera"] if cams else "—"

        cards = [
            ("Images", str(t.get("images_scanned", 0))),
            ("With GPS", str(t.get("with_gps", 0))),
            ("Cameras", str(t.get("unique_cameras", 0))),
            ("Likely AI", str(ai.get("likely_ai_count", 0))),
            ("Avg AI Score", str(ai.get("average_suspicion_score", 0))),
            ("Total Size", sz.get("total_human", "—")),
        ]
        for label, value in cards:
            card = ttk.Frame(self.cards, style="Panel.TFrame")
            card.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            ttk.Label(card, text=value, style="CardBig.TLabel").pack(anchor="w", padx=12, pady=(10, 0))
            ttk.Label(card, text=label, style="CardLbl.TLabel").pack(anchor="w", padx=12, pady=(0, 10))

        line = []
        if top_cam != "—":
            line.append(f"Top camera: {top_cam}")
        if dr:
            line.append(f"Dates: {dr.get('earliest','?')[:10]} → {dr.get('latest','?')[:10]}")
        clusters = (summary.get("gps") or {}).get("clusters", [])
        if clusters:
            line.append(f"{len(clusters)} GPS cluster(s)")
        anomalies = summary.get("anomalies", {})
        noexif = len(anomalies.get("images_without_any_exif", []))
        if noexif:
            line.append(f"{noexif} without any EXIF")
        if line:
            ttk.Label(self, text="   •   ".join(line), style="Sub.TLabel").pack(anchor="w", padx=20, pady=(2, 0))

    def _populate_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for rec in self.filtered:
            meta = rec.get("metadata") or {}
            ex = meta.get("exif") or {}
            img = meta.get("image") or {}
            fname = (rec.get("file") or {}).get("filename", "?")
            cam = f"{ex.get('Make','')} {ex.get('Model','')}".strip() or "—"
            dt = str(ex.get("DateTimeOriginal", "") or "—")[:19]
            res = f"{img.get('width','?')}x{img.get('height','?')}" if img.get("width") else "—"
            gps = "✓" if (meta.get("gps") or {}).get("decimal", {}).get("latitude") is not None else ""
            ai = meta.get("ai_indicators") or {}
            verdict = ai.get("verdict", "—")
            ai_disp = {"likely_ai": "⚠ likely", "possibly_ai": "? possibly",
                       "likely_camera": "camera", "inconclusive": "—"}.get(verdict, verdict)
            self.tree.insert("", "end", values=(fname, cam, dt, res, gps, ai_disp))

    def _apply_filter(self):
        q = self.search_var.get().strip().lower()
        if not q:
            self.filtered = list(self.records)
        else:
            self.filtered = []
            for rec in self.records:
                meta = rec.get("metadata") or {}
                ex = meta.get("exif") or {}
                fname = (rec.get("file") or {}).get("filename", "")
                hay = f"{fname} {ex.get('Make','')} {ex.get('Model','')} {ex.get('LensModel','')}".lower()
                ai = meta.get("ai_indicators") or {}
                hay += " " + ai.get("verdict", "")
                if q in hay:
                    self.filtered.append(rec)
        self._populate_table()

    def _show_detail(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self.filtered):
            return
        rec = self.filtered[idx]
        pretty = json.dumps(rec, indent=2, ensure_ascii=False, default=str)
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", pretty)
        self.detail.config(state="disabled")


if __name__ == "__main__":
    app = RavenApp()
    app.mainloop()
