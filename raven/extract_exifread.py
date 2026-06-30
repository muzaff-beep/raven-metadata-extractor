"""Extract EXIF metadata using exifread (catches tags Pillow misses)."""
from __future__ import annotations
from typing import Any
import exifread


def _clean_value(v: Any) -> Any:
    s = str(v)
    return s.strip()


def extract_exifread(path: str) -> dict:
    """
    Returns:
        {"tags": {tag_name: value_str, ...}, "error": str | None}
    Tag names are normalized by stripping the IFD prefix (e.g. "EXIF FocalLength" -> "FocalLength").
    """
    result = {"tags": {}, "error": None}
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False, strict=False)
        cleaned = {}
        for raw_name, value in tags.items():
            if raw_name in ("JPEGThumbnail", "TIFFThumbnail"):
                continue
            # raw_name looks like "EXIF FocalLength", "Image Make", "GPS GPSLatitude"
            parts = raw_name.split(" ", 1)
            short_name = parts[1] if len(parts) == 2 else raw_name
            cleaned[short_name] = _clean_value(value)
        result["tags"] = cleaned
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result
