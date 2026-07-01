#!/usr/bin/env python3
"""
Raven Metadata Extractor — GUI (Tkinter, stdlib only)
Pick a folder, extract metadata, save as JSON.
"""
from __future__ import annotations
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from raven import process_folder


class RavenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Raven Metadata Extractor")
        self.geometry("560x340")
        self.resizable(False, False)

        self.folder_path = tk.StringVar()
        self.recursive = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Choose a folder to begin.")

        pad = {"padx": 16, "pady": 8}

        tk.Label(self, text="Raven Metadata Extractor", font=("Segoe UI", 14, "bold")).pack(pady=(16, 4))
        tk.Label(self, text="Extract complete EXIF / GPS / XMP metadata from a folder of images.",
                 font=("Segoe UI", 9), fg="#555").pack(pady=(0, 12))

        row = tk.Frame(self)
        row.pack(fill="x", **pad)
        tk.Entry(row, textvariable=self.folder_path, width=50).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse...", command=self.browse).pack(side="left", padx=(8, 0))

        tk.Checkbutton(self, text="Include subfolders (recursive)", variable=self.recursive).pack(anchor="w", padx=16)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=(16, 8))

        self.run_btn = tk.Button(self, text="Extract Metadata", font=("Segoe UI", 11, "bold"),
                                  bg="#2e7d32", fg="white", command=self.run_extraction, height=2)
        self.run_btn.pack(fill="x", padx=16, pady=8)

        tk.Label(self, textvariable=self.status, font=("Segoe UI", 9), fg="#333", wraplength=520,
                 justify="left").pack(padx=16, pady=(8, 16), anchor="w")

    def browse(self):
        folder = filedialog.askdirectory(title="Select folder containing images")
        if folder:
            self.folder_path.set(folder)
            self.status.set(f"Selected: {folder}")

    def run_extraction(self):
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showwarning("No folder", "Please choose a folder first.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Invalid folder", "That folder does not exist.")
            return

        self.run_btn.config(state="disabled")
        self.progress.start(12)
        self.status.set("Processing... this may take a moment for large folders.")

        thread = threading.Thread(target=self._extract_worker, args=(folder,), daemon=True)
        thread.start()

    def _extract_worker(self, folder: str):
        try:
            results = process_folder(folder, recursive=self.recursive.get())
        except Exception as e:
            self.after(0, self._on_error, str(e))
            return
        self.after(0, self._on_done, folder, results)

    def _on_done(self, folder: str, results: list):
        self.progress.stop()
        self.run_btn.config(state="normal")

        if not results:
            self.status.set("No supported image files found in that folder.")
            messagebox.showinfo("No images", "No supported image files were found.")
            return

        default_name = os.path.join(folder, "metadata.json")
        save_path = filedialog.asksaveasfilename(
            title="Save metadata JSON",
            initialfile="metadata.json",
            initialdir=folder,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not save_path:
            self.status.set(f"Extraction done ({len(results)} images) but not saved.")
            return

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        error_count = sum(1 for r in results if r.get("errors"))
        msg = f"Processed {len(results)} image(s) -> {os.path.basename(save_path)}"
        if error_count:
            msg += f"\n{error_count} file(s) had partial extraction issues (see 'errors' field)."
        self.status.set(msg)
        messagebox.showinfo("Done", msg)

    def _on_error(self, message: str):
        self.progress.stop()
        self.run_btn.config(state="normal")
        self.status.set(f"Error: {message}")
        messagebox.showerror("Extraction failed", message)


if __name__ == "__main__":
    app = RavenApp()
    app.mainloop()
