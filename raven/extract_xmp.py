"""Extract XMP metadata embedded in image files, using Pillow's built-in getxmp()."""
from __future__ import annotations
from typing import Any

from PIL import Image


def _flatten_xmp(node: Any, out: dict) -> None:
    """
    Recursively flatten the nested dict returned by Image.getxmp() into a flat
    {field_name: value} dict, matching the shape the rest of raven expects.

    getxmp() shape (Pillow >= 8.3): nested dict keyed by local tag names, with
    RDF Bag/Seq/Alt containers appearing as {"Bag": {"li": [...]}} etc, and
    "xmpmeta" / "RDF" / "Description" as pure structural wrappers.
    """
    STRUCTURAL = {"xmpmeta", "RDF", "Description"}
    CONTAINER_KEYS = {"Bag", "Seq", "Alt"}

    if not isinstance(node, dict):
        return

    for key, value in node.items():
        if key in STRUCTURAL:
            _flatten_xmp(value, out)
            continue

        if isinstance(value, dict):
            # RDF container (Bag/Seq/Alt) holding a list under "li"
            container_key = next((k for k in CONTAINER_KEYS if k in value), None)
            if container_key is not None:
                li = value[container_key].get("li") if isinstance(value[container_key], dict) else None
                if li is None:
                    out[key] = value
                elif isinstance(li, list):
                    out[key] = [str(x) for x in li]
                else:
                    out[key] = [str(li)]
                continue
            # Description can nest directly under an arbitrary field too
            if "Description" in value:
                _flatten_xmp(value, out)
                continue
            # Otherwise it's a genuine nested struct we don't recognize; keep as-is
            if key not in out:
                out[key] = value
            continue

        if isinstance(value, list):
            out[key] = [str(x) for x in value]
            continue

        # Plain scalar value
        out[key] = value


def extract_xmp(path: str) -> dict:
    """
    Returns:
        {"xmp": {field: value, ...}, "present": bool, "error": str | None}

    Uses PIL.Image.Image.getxmp(), which:
      - works for JPEG, PNG, and TIFF (unlike a manual "<x:xmpmeta" byte search)
      - parses XML via defusedxml internally (safer than raw ElementTree)
      - returns {} (not None) when no XMP block exists
    """
    result = {"xmp": {}, "present": False, "error": None}
    try:
        with Image.open(path) as img:
            raw = img.getxmp()
        if not raw:
            return result
        result["present"] = True
        fields: dict = {}
        _flatten_xmp(raw, fields)
        result["xmp"] = fields
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result
