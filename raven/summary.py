"""
Build a comprehensive summary report from a list of per-image metadata records.
Covers: camera/lens breakdown, GPS clustering, date timeline, format/size/resolution
stats, missing-metadata anomalies, and AI-generation indicators.
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Optional


def _exif(rec: dict) -> dict:
    return (rec.get("metadata") or {}).get("exif") or {}


def _parse_exif_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:len(fmt) + 4], fmt)
        except ValueError:
            continue
    m = re.match(r"(\d{4})[:\-](\d{2})[:\-](\d{2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _cluster_gps(points: list[tuple[float, float]], precision: int = 2) -> list[dict]:
    """Simple grid clustering by rounding lat/lon. precision=2 ~ 1.1km cells."""
    buckets: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
    for lat, lon in points:
        key = (round(lat, precision), round(lon, precision))
        buckets[key].append((lat, lon))
    clusters = []
    for (klat, klon), pts in buckets.items():
        clusters.append({
            "center": {"latitude": klat, "longitude": klon},
            "count": len(pts),
            "google_maps_url": f"https://maps.google.com/?q={klat},{klon}",
        })
    clusters.sort(key=lambda c: c["count"], reverse=True)
    return clusters


def build_summary(records: list[dict], source_folder: str = "") -> dict:
    total = len(records)
    cameras = Counter()
    lenses = Counter()
    formats = Counter()
    extensions = Counter()
    resolutions = Counter()
    modes = Counter()

    sizes = []
    resolutions_px = []
    dates = []
    gps_points = []
    gps_images = 0

    missing_all_exif = []
    missing_gps = 0
    missing_datetime = 0
    error_files = []

    ai_likely = []
    ai_possible = []
    ai_scores = []

    for rec in records:
        fname = (rec.get("file") or {}).get("filename", "?")
        ex = _exif(rec)
        meta = rec.get("metadata") or {}
        img = meta.get("image") or {}

        if rec.get("errors"):
            error_files.append({"filename": fname, "errors": rec["errors"]})

        # camera / lens
        make = str(ex.get("Make", "")).strip()
        model = str(ex.get("Model", "")).strip()
        if make or model:
            cameras[f"{make} {model}".strip()] += 1
        lens = str(ex.get("LensModel", "") or ex.get("LensMake", "")).strip()
        if lens:
            lenses[lens] += 1

        # format / mode / resolution
        fmt = img.get("format")
        if fmt:
            formats[fmt] += 1
        mode = img.get("mode")
        if mode:
            modes[mode] += 1
        ext = (rec.get("file") or {}).get("extension")
        if ext:
            extensions[ext] += 1
        w, h = img.get("width"), img.get("height")
        if w and h:
            resolutions[f"{w}x{h}"] += 1
            resolutions_px.append(w * h)

        # size
        sz = (rec.get("file") or {}).get("size_bytes")
        if isinstance(sz, (int, float)):
            sizes.append(sz)

        # datetime
        dt = _parse_exif_datetime(ex.get("DateTimeOriginal") or ex.get("DateTime"))
        if dt:
            dates.append(dt)
        else:
            missing_datetime += 1

        # gps
        gps = meta.get("gps")
        dec = (gps or {}).get("decimal") or {}
        if dec.get("latitude") is not None and dec.get("longitude") is not None:
            gps_points.append((dec["latitude"], dec["longitude"]))
            gps_images += 1
        else:
            missing_gps += 1

        # missing-all-exif anomaly
        if not ex:
            missing_all_exif.append(fname)

        # ai indicators
        ai = meta.get("ai_indicators")
        if ai:
            ai_scores.append(ai.get("suspicion_score", 0))
            if ai.get("verdict") == "likely_ai":
                ai_likely.append({"filename": fname, "score": ai.get("suspicion_score"),
                                  "signals": ai.get("signals", [])})
            elif ai.get("verdict") == "possibly_ai":
                ai_possible.append({"filename": fname, "score": ai.get("suspicion_score")})

    date_range = None
    if dates:
        dmin, dmax = min(dates), max(dates)
        date_range = {
            "earliest": dmin.isoformat(),
            "latest": dmax.isoformat(),
            "span_days": (dmax - dmin).days,
        }

    size_stats = None
    if sizes:
        size_stats = {
            "total_bytes": sum(sizes),
            "total_human": _human(sum(sizes)),
            "average_bytes": int(sum(sizes) / len(sizes)),
            "average_human": _human(sum(sizes) / len(sizes)),
            "largest_human": _human(max(sizes)),
            "smallest_human": _human(min(sizes)),
        }

    megapixels = None
    if resolutions_px:
        avg_px = sum(resolutions_px) / len(resolutions_px)
        megapixels = {
            "average_mp": round(avg_px / 1_000_000, 2),
            "max_mp": round(max(resolutions_px) / 1_000_000, 2),
            "min_mp": round(min(resolutions_px) / 1_000_000, 2),
        }

    return {
        "source_folder": source_folder,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "totals": {
            "images_scanned": total,
            "with_gps": gps_images,
            "with_errors": len(error_files),
            "unique_cameras": len(cameras),
        },
        "camera_breakdown": [{"camera": k, "count": v} for k, v in cameras.most_common()],
        "lens_breakdown": [{"lens": k, "count": v} for k, v in lenses.most_common()],
        "format_stats": {
            "formats": [{"format": k, "count": v} for k, v in formats.most_common()],
            "extensions": [{"extension": k, "count": v} for k, v in extensions.most_common()],
            "color_modes": [{"mode": k, "count": v} for k, v in modes.most_common()],
            "top_resolutions": [{"resolution": k, "count": v} for k, v in resolutions.most_common(10)],
            "megapixels": megapixels,
        },
        "size_stats": size_stats,
        "date_range": date_range,
        "gps": {
            "images_with_gps": gps_images,
            "clusters": _cluster_gps(gps_points) if gps_points else [],
        },
        "anomalies": {
            "images_without_any_exif": missing_all_exif,
            "count_without_gps": missing_gps,
            "count_without_datetime": missing_datetime,
            "files_with_errors": error_files,
        },
        "ai_indicators": {
            "average_suspicion_score": round(sum(ai_scores) / len(ai_scores), 1) if ai_scores else 0,
            "likely_ai_count": len(ai_likely),
            "possibly_ai_count": len(ai_possible),
            "likely_ai_files": ai_likely,
            "possibly_ai_files": ai_possible,
            "disclaimer": "Offline indicators only, not proof of AI generation.",
        },
    }


def _human(num_bytes: float) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
