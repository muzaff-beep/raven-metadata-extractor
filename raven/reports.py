"""
Report storage manager.

- Reports live in: <user Documents>/RavenReports/
- Filename format:  <foldername>_<YYYY-MM-DD_HH-MM-SS>.json
- A history index (history.json) tracks every saved report with its
  source folder location, name, and timestamp for the History tab.
- No subfolders are created (flat layout) to prevent confusion.
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

REPORTS_DIRNAME = "RavenReports"
HISTORY_FILE = "history.json"


def get_reports_dir() -> Path:
    """<Documents>/RavenReports, created if missing. Falls back to home if no Documents."""
    home = Path.home()
    documents = home / "Documents"
    base = documents if documents.exists() else home
    reports = base / REPORTS_DIRNAME
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def _safe_folder_name(source_folder: str) -> str:
    name = os.path.basename(os.path.normpath(source_folder)) or "scan"
    name = re.sub(r"[^A-Za-z0-9_\-]+", "_", name).strip("_")
    return name or "scan"


def build_report_filename(source_folder: str, when: Optional[datetime] = None) -> str:
    when = when or datetime.now()
    stamp = when.strftime("%Y-%m-%d_%H-%M-%S")
    return f"{_safe_folder_name(source_folder)}_{stamp}.json"


def save_report(records: list[dict], summary: dict, source_folder: str) -> dict:
    """
    Writes the full report (summary + records) to the designated folder,
    updates history index, and returns the history entry.
    """
    reports_dir = get_reports_dir()
    when = datetime.now()
    filename = build_report_filename(source_folder, when)
    filepath = reports_dir / filename

    payload = {
        "summary": summary,
        "records": records,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    entry = {
        "report_name": filename,
        "report_path": str(filepath),
        "source_folder": os.path.abspath(source_folder),
        "source_folder_name": os.path.basename(os.path.normpath(source_folder)),
        "timestamp": when.isoformat(timespec="seconds"),
        "image_count": summary.get("totals", {}).get("images_scanned", len(records)),
    }
    _append_history(reports_dir, entry)
    return entry


def _history_path(reports_dir: Optional[Path] = None) -> Path:
    reports_dir = reports_dir or get_reports_dir()
    return reports_dir / HISTORY_FILE


def _append_history(reports_dir: Path, entry: dict) -> None:
    hpath = _history_path(reports_dir)
    history = load_history()
    history.insert(0, entry)  # newest first
    with open(hpath, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def load_history() -> list[dict]:
    hpath = _history_path()
    if not hpath.exists():
        return []
    try:
        with open(hpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # Drop entries whose report file no longer exists
            return [e for e in data if os.path.exists(e.get("report_path", ""))]
        return []
    except Exception:
        return []


def load_report(report_path: str) -> Optional[dict]:
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
