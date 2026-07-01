"""
Offline AI-generation indicators.

IMPORTANT: These are *indicators*, never proof. Offline heuristics cannot
definitively determine whether an image was AI-generated. The score is a
suspicion signal to guide human review.
"""
from __future__ import annotations
from typing import Any, Optional

# Software / tool strings that strongly indicate synthetic generation
_AI_SOFTWARE_MARKERS = [
    "dall-e", "dall e", "dalle", "midjourney", "stable diffusion", "stablediffusion",
    "sdxl", "comfyui", "automatic1111", "invokeai", "leonardo.ai", "leonardo ai",
    "firefly", "adobe firefly", "flux", "imagen", "ideogram", "novelai",
    "playground.ai", "playground ai", "runway", "gpt-4o", "gpt image", "grok",
    "nano banana", "gemini", "recraft", "krea", "generated with ai", "ai generated",
]

# EXIF keys whose presence indicates a real capture device
_CAMERA_EVIDENCE_KEYS = [
    "Make", "Model", "LensModel", "LensMake", "ExposureTime", "FNumber",
    "ISOSpeedRatings", "FocalLength", "DateTimeOriginal", "SerialNumber",
    "BodySerialNumber", "GPSLatitude",
]


def _collect_text_blob(exif: dict, xmp: Optional[dict]) -> str:
    parts = []
    for k in ("Software", "ProcessingSoftware", "HostComputer", "ImageDescription",
              "UserComment", "Artist", "Copyright"):
        v = exif.get(k)
        if v:
            parts.append(str(v))
    if xmp:
        for k, v in xmp.items():
            parts.append(f"{k} {v}")
    return " ".join(parts).lower()


def _check_c2pa(raw_bytes: bytes) -> bool:
    """
    Detect a C2PA / Content Credentials manifest.
    C2PA embeds a JUMBF box; the ASCII markers below appear in the manifest store.
    """
    markers = [b"c2pa", b"jumbf", b"contentcred", b"urn:uuid:", b"cai\x00", b"c2pa.assertions"]
    lowered = raw_bytes[:200000] + raw_bytes[-200000:]  # manifests sit near head or tail
    low = lowered.lower()
    hits = sum(1 for m in markers if m in low)
    # require the c2pa/jumbf anchor plus at least one supporting marker
    has_anchor = (b"c2pa" in low) or (b"jumbf" in low and b"contentcred" in low)
    return has_anchor and hits >= 2


def _fft_grid_score(path: str) -> Optional[float]:
    """
    Frequency-domain periodicity score in [0,1].
    Diffusion/GAN images sometimes leave periodic spectral peaks. Higher = more
    periodic structure = weakly more suspicious. Returns None if unavailable.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            g = img.convert("L")
            g.thumbnail((512, 512))
            arr = np.asarray(g, dtype=np.float64)
        if arr.size == 0 or arr.ndim != 2:
            return None
        arr = arr - arr.mean()
        spec = np.abs(np.fft.fftshift(np.fft.fft2(arr)))
        spec = np.log1p(spec)
        # Remove DC/low-freq center
        h, w = spec.shape
        cy, cx = h // 2, w // 2
        r = max(4, min(h, w) // 20)
        spec[cy - r:cy + r, cx - r:cx + r] = 0.0
        mean = spec.mean()
        std = spec.std()
        if std == 0:
            return 0.0
        # Fraction of energy in sharp high-frequency peaks (periodic artifacts)
        peak_mask = spec > (mean + 4.0 * std)
        score = float(peak_mask.sum()) / float(spec.size)
        # Normalize into a comfortable 0..1 band (empirical scaling)
        return round(min(1.0, score * 800.0), 4)
    except Exception:
        return None


def analyze_ai_indicators(path: str, exif: dict, xmp: Optional[dict],
                          raw_bytes: Optional[bytes] = None) -> dict:
    """
    Returns a structured indicator block. Never claims certainty.
        {
          "verdict": "likely_ai" | "possibly_ai" | "likely_camera" | "inconclusive",
          "suspicion_score": 0..100,
          "signals": [ ... human-readable strings ... ],
          "c2pa_manifest": bool,
          "fft_periodicity": float | None,
          "has_camera_evidence": bool
        }
    """
    signals: list[str] = []
    score = 0

    blob = _collect_text_blob(exif, xmp)
    matched_markers = [m for m in _AI_SOFTWARE_MARKERS if m in blob]
    if matched_markers:
        score += 60
        signals.append(f"AI tool string(s) in metadata: {', '.join(sorted(set(matched_markers)))}")

    camera_hits = [k for k in _CAMERA_EVIDENCE_KEYS if exif.get(k) not in (None, "")]
    has_camera_evidence = len(camera_hits) >= 3
    if has_camera_evidence:
        score -= 30
        signals.append(f"Camera-capture EXIF present ({len(camera_hits)} fields)")
    elif len(camera_hits) == 0:
        score += 25
        signals.append("No camera-capture EXIF fields at all")
    else:
        score += 10
        signals.append(f"Sparse camera EXIF ({len(camera_hits)} field(s))")

    c2pa = False
    if raw_bytes:
        c2pa = _check_c2pa(raw_bytes)
        if c2pa:
            # C2PA can mark AI OR authentic-capture provenance; flag for review either way
            score += 20
            signals.append("C2PA / Content Credentials manifest detected (inspect provenance)")

    fft = _fft_grid_score(path)
    if fft is not None:
        if fft > 0.5:
            score += 20
            signals.append(f"High frequency-domain periodicity (FFT score {fft})")
        elif fft > 0.25:
            score += 8
            signals.append(f"Moderate frequency-domain periodicity (FFT score {fft})")

    score = max(0, min(100, score))

    if score >= 65:
        verdict = "likely_ai"
    elif score >= 40:
        verdict = "possibly_ai"
    elif has_camera_evidence and score < 20:
        verdict = "likely_camera"
    else:
        verdict = "inconclusive"

    if not signals:
        signals.append("No strong indicators either way")

    return {
        "verdict": verdict,
        "suspicion_score": score,
        "signals": signals,
        "c2pa_manifest": c2pa,
        "fft_periodicity": fft,
        "has_camera_evidence": has_camera_evidence,
        "disclaimer": "Offline indicators only, not proof of AI generation.",
    }
