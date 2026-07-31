"""Extract EXIF metadata using Pillow."""
from __future__ import annotations
from typing import Any, Optional
from PIL import Image
from PIL import ExifTags
from PIL.ExifTags import TAGS, GPSTAGS

from .tag_decoder import TagDecoder
from .gps import build_gps_block


def _clean_value(v: Any) -> Any:
    """Convert non-JSON-serializable EXIF value types into plain python types."""
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", errors="replace").strip("\x00").strip()
        except Exception:
            return v.hex()
    if hasattr(v, "numerator") and hasattr(v, "denominator"):
        try:
            return v.numerator / v.denominator if v.denominator else None
        except ZeroDivisionError:
            return None
    if isinstance(v, tuple):
        return [_clean_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _clean_value(x) for k, x in v.items()}
    return v


def extract_pillow(path: str) -> dict:
    """
    Returns:
        {
          "image": {width, height, mode, format},
          "exif": {tag_name: decoded_value, ...},
          "exif_raw": {tag_name: raw_value, ...},
          "gps": {...} | None,
          "error": str | None
        }
    """
    result = {"image": {}, "exif": {}, "exif_raw": {}, "gps": None, "error": None}
    try:
        with Image.open(path) as img:
            result["image"] = {
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": img.format,
            }
            exif = img.getexif()
            if not exif:
                return result

            flat_raw = {}
            for tag_id, value in exif.items():
                name = TAGS.get(tag_id, f"Tag_0x{tag_id:04X}")
                flat_raw[name] = _clean_value(value)

            # Sub-IFDs (Exif, GPS) — Pillow exposes them via get_ifd
            gps_ifd_raw = {}
            try:
                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                for tag_id, value in exif_ifd.items():
                    name = TAGS.get(tag_id, f"Tag_0x{tag_id:04X}")
                    flat_raw[name] = _clean_value(value)
            except Exception:
                pass
            try:
                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                for tag_id, value in gps_ifd.items():
                    name = GPSTAGS.get(tag_id, f"GPSTag_0x{tag_id:04X}")
                    gps_ifd_raw[name] = _clean_value(value)
            except Exception:
                pass

            result["exif_raw"] = flat_raw

            decoded = {}
            for name, raw in flat_raw.items():
                decoded[name] = TagDecoder.decode(name, raw)
            result["exif"] = decoded

            if gps_ifd_raw:
                result["gps"] = build_gps_block(gps_ifd_raw)

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result
