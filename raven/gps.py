"""GPS coordinate conversion: DMS rationals -> decimal degrees."""
from __future__ import annotations
from typing import Any, Optional


def _rational_to_float(r: Any) -> Optional[float]:
    try:
        if hasattr(r, "numerator") and hasattr(r, "denominator"):
            return float(r.numerator) / float(r.denominator) if r.denominator else None
        if isinstance(r, (tuple, list)) and len(r) == 2:
            return float(r[0]) / float(r[1]) if r[1] else None
        return float(r)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def dms_to_decimal(dms: Any, ref: Optional[str]) -> Optional[float]:
    """Convert a (deg, min, sec) tuple of rationals + ref ('N','S','E','W') to signed decimal degrees."""
    if not dms or len(dms) != 3:
        return None
    deg = _rational_to_float(dms[0])
    minutes = _rational_to_float(dms[1])
    seconds = _rational_to_float(dms[2])
    if deg is None or minutes is None or seconds is None:
        return None
    decimal = deg + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ("S", "W"):
        decimal = -decimal
    return round(decimal, 8)


def build_gps_block(gps_ifd: dict) -> Optional[dict]:
    """
    Build a complete GPS metadata block from a raw GPS IFD dict
    (keys are GPS tag names as produced by PillowExtractor / ExifreadExtractor).
    Includes both raw values and decoded decimal lat/lon/altitude.
    """
    if not gps_ifd:
        return None

    lat_dms = gps_ifd.get("GPSLatitude")
    lat_ref = gps_ifd.get("GPSLatitudeRef")
    lon_dms = gps_ifd.get("GPSLongitude")
    lon_ref = gps_ifd.get("GPSLongitudeRef")

    latitude = dms_to_decimal(lat_dms, lat_ref) if lat_dms else None
    longitude = dms_to_decimal(lon_dms, lon_ref) if lon_dms else None

    altitude_raw = gps_ifd.get("GPSAltitude")
    altitude = _rational_to_float(altitude_raw) if altitude_raw is not None else None
    if altitude is not None and gps_ifd.get("GPSAltitudeRef") in (1, "1", b"\x01"):
        altitude = -altitude

    block = {
        "raw": {k: (str(v) if not isinstance(v, (int, float, str, type(None))) else v)
                for k, v in gps_ifd.items()},
        "decimal": {
            "latitude": latitude,
            "longitude": longitude,
            "altitude_m": round(altitude, 3) if altitude is not None else None,
        },
    }
    if latitude is not None and longitude is not None:
        block["decimal"]["google_maps_url"] = f"https://maps.google.com/?q={latitude},{longitude}"
    return block
