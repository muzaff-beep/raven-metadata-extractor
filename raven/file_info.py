"""Collect file-system level info: size, hashes, mime type, timestamps."""
from __future__ import annotations
import hashlib
import mimetypes
import os
from datetime import datetime, timezone
from typing import Any


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _sha256(path: str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def collect_file_info(path: str) -> dict:
    stat = os.stat(path)
    mime, _ = mimetypes.guess_type(path)
    return {
        "filename": os.path.basename(path),
        "path": os.path.abspath(path),
        "size_bytes": stat.st_size,
        "size_human": _human_size(stat.st_size),
        "mime_type": mime or "application/octet-stream",
        "extension": os.path.splitext(path)[1].lower().lstrip("."),
        "modified_at": _iso(stat.st_mtime),
        # st_ctime is inode/metadata-change time on Linux, not creation time;
        # st_birthtime (true creation time) only exists on macOS/BSD, so fall
        # back to ctime there and label it accurately everywhere.
        "created_at": _iso(getattr(stat, "st_birthtime", stat.st_ctime)),
        "created_at_is_true_birthtime": hasattr(stat, "st_birthtime"),
        "metadata_changed_at": _iso(stat.st_ctime),
        "sha256": _sha256(path),
    }
