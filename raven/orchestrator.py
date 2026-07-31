"""Walk a folder of images and produce one merged metadata record per file."""
from __future__ import annotations
import os
from typing import Any, Iterable

from .file_info import collect_file_info
from .extract_pillow import extract_pillow
from .extract_exifread import extract_exifread
from .extract_xmp import extract_xmp
from .ai_detect import analyze_ai_indicators

SUPPORTED_EXTENSIONS = {
    "jpg", "jpeg", "png", "tiff", "tif", "webp", "heic", "heif", "bmp", "gif"
}


def _merge_exif(pillow_exif: dict, exifread_tags: dict) -> dict:
    """
    Merge two EXIF sources. Pillow values win when both present (already decoded
    via TagDecoder); exifread fills in anything Pillow didn't expose.
    """
    merged = dict(pillow_exif)
    for k, v in exifread_tags.items():
        if k not in merged or merged[k] in (None, ""):
            merged[k] = v
    return merged


def process_image(path: str) -> dict:
    """Build the complete metadata record for a single image file."""
    record: dict = {"file": None, "metadata": {}, "errors": []}

    try:
        record["file"] = collect_file_info(path)
    except Exception as e:
        record["errors"].append(f"file_info: {type(e).__name__}: {e}")
        record["file"] = {"filename": os.path.basename(path), "path": os.path.abspath(path)}

    pillow_result = extract_pillow(path)
    if pillow_result.get("error"):
        record["errors"].append(f"pillow: {pillow_result['error']}")

    exifread_result = extract_exifread(path)
    if exifread_result.get("error"):
        record["errors"].append(f"exifread: {exifread_result['error']}")

    xmp_result = extract_xmp(path)
    if xmp_result.get("error"):
        record["errors"].append(f"xmp: {xmp_result['error']}")

    merged_exif = _merge_exif(pillow_result.get("exif", {}), exifread_result.get("tags", {}))

    # AI-generation indicators (offline heuristics + C2PA + FFT)
    ai_block = None
    try:
        raw_bytes = None
        try:
            with open(path, "rb") as fh:
                raw_bytes = fh.read()
        except Exception:
            raw_bytes = None
        ai_block = analyze_ai_indicators(
            path, merged_exif, xmp_result.get("xmp") if xmp_result.get("present") else None, raw_bytes
        )
    except Exception as e:
        record["errors"].append(f"ai_detect: {type(e).__name__}: {e}")

    record["metadata"] = {
        "image": pillow_result.get("image", {}),
        "exif": merged_exif,
        "gps": pillow_result.get("gps"),
        "xmp": xmp_result.get("xmp") if xmp_result.get("present") else None,
        "ai_indicators": ai_block,
    }
    return record


def find_images(folder: str, recursive: bool = False) -> Iterable[str]:
    if recursive:
        for root, _, files in os.walk(folder):
            for fn in sorted(files):
                ext = os.path.splitext(fn)[1].lower().lstrip(".")
                if ext in SUPPORTED_EXTENSIONS:
                    yield os.path.join(root, fn)
    else:
        for fn in sorted(os.listdir(folder)):
            full = os.path.join(folder, fn)
            if os.path.isfile(full):
                ext = os.path.splitext(fn)[1].lower().lstrip(".")
                if ext in SUPPORTED_EXTENSIONS:
                    yield full


def process_folder(folder: str, recursive: bool = False, on_progress=None) -> list[dict]:
    """
    on_progress(index, total, path, record) is called after each image is
    processed, if provided -- lets the GUI show a live scrolling log and
    accurate progress/pagination without changing the return value or
    blocking behavior for existing callers that don't pass it.
    """
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Not a folder: {folder}")
    paths = list(find_images(folder, recursive=recursive))
    total = len(paths)
    results = []
    for i, path in enumerate(paths, start=1):
        record = process_image(path)
        results.append(record)
        if on_progress:
            try:
                on_progress(i, total, path, record)
            except Exception:
                pass  # never let a logging/UI callback break the scan
    return results
