"""Extract XMP metadata embedded in image files, using proper XML parsing (not regex)."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

_XMP_START = b"<x:xmpmeta"
_XMP_END = b"</x:xmpmeta>"

_NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "photoshop": "http://ns.adobe.com/photoshop/1.0/",
    "exif": "http://ns.adobe.com/exif/1.0/",
    "tiff": "http://ns.adobe.com/tiff/1.0/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "crs": "http://ns.adobe.com/camera-raw-settings/1.0/",
}


def _find_xmp_block(raw_bytes: bytes) -> Optional[bytes]:
    start = raw_bytes.find(_XMP_START)
    if start == -1:
        return None
    end = raw_bytes.find(_XMP_END, start)
    if end == -1:
        return None
    return raw_bytes[start:end + len(_XMP_END)]


def _local_tag(tag: str) -> str:
    """Strip XML namespace braces: '{ns}TagName' -> 'TagName'."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _extract_text_or_list(elem: ET.Element) -> Any:
    """
    Handles plain text values and RDF Bag/Seq/Alt lists (used for keywords,
    creator lists, subject lists, etc).
    """
    bag = elem.find("rdf:Bag", _NS) or elem.find("rdf:Seq", _NS) or elem.find("rdf:Alt", _NS)
    if bag is not None:
        items = [li.text.strip() for li in bag.findall("rdf:li", _NS) if li.text]
        return items
    if elem.text and elem.text.strip():
        return elem.text.strip()
    return None


def extract_xmp(path: str) -> dict:
    """
    Returns:
        {"xmp": {field: value, ...}, "present": bool, "error": str | None}
    """
    result = {"xmp": {}, "present": False, "error": None}
    try:
        with open(path, "rb") as f:
            raw = f.read()
        block = _find_xmp_block(raw)
        if block is None:
            return result
        result["present"] = True

        try:
            text = block.decode("utf-8", errors="replace")
        except Exception:
            text = block.decode("latin-1", errors="replace")

        root = ET.fromstring(text)
        fields: dict = {}

        # Walk every Description element's attributes (simple key="value" XMP fields)
        for desc in root.iter():
            if _local_tag(desc.tag) == "Description":
                for attr, val in desc.attrib.items():
                    fields[_local_tag(attr)] = val

        # Walk child elements for structured / list values (dc:subject, dc:creator, etc)
        for elem in root.iter():
            local = _local_tag(elem.tag)
            if local in ("RDF", "Description", "xmpmeta"):
                continue
            if local in fields:
                continue
            value = _extract_text_or_list(elem)
            if value:
                fields[local] = value

        result["xmp"] = fields
    except ET.ParseError as e:
        result["error"] = f"XMP XML parse error: {e}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result
