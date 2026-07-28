"""Walk a folder of images and produce one merged metadata record per file."""
from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable, Optional, Callable

from .file_info import collect_file_info
from .extract_pillow import extract_pillow
from .extract_exifread import extract_exifread
from .extract_xmp import extract_xmp
from .ai_detect import analyze_ai_indicators

SUPPORTED_EXTENSIONS = {
    "jpg", "jpeg", "png", "tiff", "tif", "webp", "heic", "heif", "bmp", "gif"
}

# Default number of worker threads for parallel processing
DEFAULT_WORKERS = min(8, (os.cpu_count() or 4) + 1)


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


def process_folder(
    folder: str,
    recursive: bool = False,
    on_progress: Optional[Callable[[int, int, str, dict], None]] = None,
    max_workers: int = DEFAULT_WORKERS,
) -> list[dict]:
    """
    Process all images in a folder, optionally in parallel.

    Args:
        folder: Path to the folder containing images.
        recursive: If True, scan subfolders recursively.
        on_progress: Callback called after each image is processed:
                     on_progress(index, total, path, record). Lets the GUI
                     show a live scrolling log and accurate progress/pagination.
        max_workers: Number of worker threads for parallel processing.
                     Use 1 for sequential processing (default: CPU-based heuristic).

    Returns:
        List of metadata records, one per image, in the order they were found.

    Note:
        Parallel processing speeds up I/O-bound operations (reading files,
        parsing metadata) but may affect the order of progress callbacks.
        Results are always returned in the original file order.
    """
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Not a folder: {folder}")
    paths = list(find_images(folder, recursive=recursive))
    total = len(paths)
    results: list[Optional[dict]] = [None] * total

    if max_workers <= 1:
        # Sequential processing - preserves original behavior exactly
        for i, path in enumerate(paths):
            record = process_image(path)
            results[i] = record
            if on_progress:
                try:
                    on_progress(i + 1, total, path, record)
                except Exception:
                    pass  # never let a logging/UI callback break the scan
        return results  # type: ignore

    # Parallel processing with ThreadPoolExecutor
    def _process_with_index(idx_path: tuple[int, str]) -> tuple[int, dict]:
        idx, path = idx_path
        record = process_image(path)
        return idx, record

    indexed_paths = list(enumerate(paths))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_with_index, item): item[0] for item in indexed_paths}
        completed = 0
        for future in as_completed(futures):
            idx, record = future.result()
            results[idx] = record
            completed += 1
            if on_progress:
                try:
                    # Report in completion order, but include correct index
                    on_progress(completed, total, paths[idx], record)
                except Exception:
                    pass  # never let a logging/UI callback break the scan

    return [r for r in results if r is not None]  # type: ignore
