"""
Offline AI-generation indicators, combining:
  1. C2PA / Content Credentials manifest reading (c2pa_reader.py)   -- strongest signal
  2. Metadata text markers (tool/software strings in EXIF/XMP)      -- strong signal
  3. EXIF-absence pattern analysis                                  -- weak/moderate signal
  4. Frequency-domain periodicity (FFT)                             -- weak signal
  5. Optional local ML classifier (ml_classifier.py)                -- moderate signal, narrow scope

IMPORTANT: These are *indicators*, never proof. No offline heuristic and no
lightweight bundled model can definitively determine whether an image was
AI-generated, especially against modern diffusion models. The score is a
suspicion signal to guide human review, not a verdict.

Design principles behind this version:
  - Evidence is tiered by reliability, not summed as arbitrary flat points.
    A single strong signal (verified C2PA claim, explicit tool string) can
    settle the verdict on its own; weak signals (FFT, EXIF absence) can only
    nudge a score that's otherwise ambiguous, never dominate it.
  - "No camera EXIF" is deliberately NOT treated as strong AI evidence, because
    social platforms (WhatsApp, Instagram, Discord, Twitter/X, etc.) strip or
    rewrite EXIF on nearly every real photo that passes through them. Instead
    we distinguish "stripped/re-encoded by a known platform pattern" from
    "no EXIF and no re-encode fingerprint," and weight the latter only lightly.
  - Every signal that fires is shown to the user with its own weight and
    reasoning -- never just a bare final number.
"""
from __future__ import annotations
from typing import Any, Optional

from .c2pa_reader import read_c2pa_manifest
from . import ml_classifier

# Software / tool strings that strongly indicate synthetic generation
_AI_SOFTWARE_MARKERS = [
    "dall-e", "dall e", "dalle", "midjourney", "stable diffusion", "stablediffusion",
    "sdxl", "comfyui", "automatic1111", "invokeai", "leonardo.ai", "leonardo ai",
    "firefly", "adobe firefly", "flux", "imagen", "ideogram", "novelai",
    "playground.ai", "playground ai", "runway", "gpt-4o", "gpt image",
    "nano banana", "recraft", "krea", "generated with ai", "ai generated",
]

# Ambiguous words that are only meaningful as AI-tool markers when paired with
# an AI-ish context word (avoids false positives from unrelated captions/names
# mentioning "Grok" or "Gemini" the constellation/product in another sense).
_AMBIGUOUS_MARKERS_NEED_CONTEXT = {
    "grok": ["xai", "image", "generat"],
    "gemini": ["google", "image", "generat", "nano banana"],
}

# EXIF keys whose presence indicates a real capture device
_CAMERA_EVIDENCE_KEYS = [
    "Make", "Model", "LensModel", "LensMake", "ExposureTime", "FNumber",
    "ISOSpeedRatings", "FocalLength", "DateTimeOriginal", "SerialNumber",
    "BodySerialNumber", "GPSLatitude",
]

# Known re-encode fingerprints left by social/messaging platforms that strip
# EXIF as a side effect of re-compressing images -- NOT evidence of AI origin.
# Matched against Software/ProcessingSoftware/HostComputer strings.
_KNOWN_REENCODE_SOFTWARE = [
    "whatsapp", "instagram", "facebook", "messenger", "telegram", "discord",
    "twitter", " x-", "snapchat", "imessage", "google photos", "photos.google",
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


def _fft_grid_score(path: str) -> Optional[float]:
    """
    Frequency-domain periodicity score in [0,1].
    Some GAN-era generators leave periodic spectral peaks from transposed-
    convolution upsampling. Modern diffusion models (SDXL, Flux, Midjourney v6+)
    largely do not exhibit this artifact, so treat this as a weak, dated signal
    -- present mainly to catch older/simpler generators and upscalers.
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
        h, w = spec.shape
        cy, cx = h // 2, w // 2
        r = max(4, min(h, w) // 20)
        spec[cy - r:cy + r, cx - r:cx + r] = 0.0
        mean = spec.mean()
        std = spec.std()
        if std == 0:
            return 0.0
        peak_mask = spec > (mean + 4.0 * std)
        score = float(peak_mask.sum()) / float(spec.size)
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
          "confidence": "low" | "medium" | "high",   # how much to trust the score itself
          "signals": [ {"label": str, "weight": int, "tier": str}, ... ],
          "c2pa": { ... c2pa_reader output ... },
          "ml_classifier": { ... ml_classifier output ... },
          "fft_periodicity": float | None,
          "has_camera_evidence": bool,
          "disclaimer": str,
        }
    """
    signals: list[dict] = []
    score = 0
    strong_signal_fired = False  # a single tier-1 signal can settle the verdict

    # --- Tier 1: C2PA manifest with a resolvable digitalSourceType ----------
    c2pa_result = read_c2pa_manifest(path)
    if c2pa_result["present"] and c2pa_result["ai_generated"] is True:
        score += 70
        strong_signal_fired = True
        agent = ", ".join(c2pa_result["software_agents"]) or c2pa_result.get("claim_generator") or "unknown tool"
        signals.append({
            "label": f"C2PA manifest declares AI/synthetic origin (agent: {agent})",
            "weight": 70, "tier": "strong",
        })
    elif c2pa_result["present"] and c2pa_result["ai_generated"] is False:
        score -= 40
        strong_signal_fired = True
        signals.append({
            "label": "C2PA manifest declares a real capture/edit source type",
            "weight": -40, "tier": "strong",
        })
    elif c2pa_result["present"]:
        score += 10
        signals.append({
            "label": "C2PA manifest present but source type unresolved (inspect manually)",
            "weight": 10, "tier": "moderate",
        })
    if c2pa_result.get("error"):
        signals.append({"label": f"C2PA read error: {c2pa_result['error']}", "weight": 0, "tier": "info"})

    # --- Tier 1: explicit AI tool name in metadata ---------------------------
    blob = _collect_text_blob(exif, xmp)
    matched_markers = [m for m in _AI_SOFTWARE_MARKERS if m in blob]
    for word, context_hints in _AMBIGUOUS_MARKERS_NEED_CONTEXT.items():
        if word in blob and any(hint in blob for hint in context_hints):
            matched_markers.append(word)
    if matched_markers:
        score += 65
        strong_signal_fired = True
        signals.append({
            "label": f"AI tool string(s) in metadata: {', '.join(sorted(set(matched_markers)))}",
            "weight": 65, "tier": "strong",
        })

    # --- Tier 2: optional local ML classifier --------------------------------
    ml_result = ml_classifier.classify_image(path)
    if ml_result["available"] and ml_result["ai_probability"] is not None:
        p = ml_result["ai_probability"]
        # Scaled moderately -- never enough alone to reach "likely_ai" given its
        # narrow (face-deepfake) scope and modest published accuracy.
        contribution = round((p - 0.5) * 50)  # -25..+25
        score += contribution
        signals.append({
            "label": f"Local ML classifier: {p*100:.1f}% ({ml_result['scope']})",
            "weight": contribution, "tier": "moderate",
        })

    # --- Tier 3: camera EXIF evidence (fixed absence-logic) ------------------
    camera_hits = [k for k in _CAMERA_EVIDENCE_KEYS if exif.get(k) not in (None, "")]
    has_camera_evidence = len(camera_hits) >= 3
    looks_reencoded = any(m in blob for m in _KNOWN_REENCODE_SOFTWARE)

    if has_camera_evidence:
        score -= 25
        signals.append({
            "label": f"Camera-capture EXIF present ({len(camera_hits)} fields)",
            "weight": -25, "tier": "moderate",
        })
    elif looks_reencoded:
        # No EXIF, but bears a known platform re-encode fingerprint: this is
        # the single most common reason real photos lose EXIF. Not evidence
        # of AI origin, so contribute nothing either way -- just note it.
        signals.append({
            "label": "No camera EXIF, but re-encode fingerprint suggests platform "
                     "stripping (WhatsApp/Instagram/etc.), not AI origin",
            "weight": 0, "tier": "info",
        })
    elif len(camera_hits) == 0:
        # No EXIF and no known re-encode explanation: mildly suspicious, but
        # this alone is weak -- plenty of legitimate sources (screenshots,
        # scans, downloaded stock/CC images, manually stripped photos) hit
        # this too, so keep the weight small.
        score += 12
        signals.append({
            "label": "No camera-capture EXIF and no known re-encode fingerprint",
            "weight": 12, "tier": "weak",
        })
    else:
        score += 5
        signals.append({
            "label": f"Sparse camera EXIF ({len(camera_hits)} field(s))",
            "weight": 5, "tier": "weak",
        })

    # --- Tier 3: FFT periodicity (weak, dated signal) ------------------------
    fft = _fft_grid_score(path)
    if fft is not None:
        if fft > 0.5:
            score += 12
            signals.append({
                "label": f"High frequency-domain periodicity (FFT score {fft}) "
                         "-- more common in older GAN/upscaler outputs",
                "weight": 12, "tier": "weak",
            })
        elif fft > 0.25:
            score += 5
            signals.append({
                "label": f"Moderate frequency-domain periodicity (FFT score {fft})",
                "weight": 5, "tier": "weak",
            })

    score = max(0, min(100, score))

    # --- Verdict + confidence -------------------------------------------------
    if strong_signal_fired:
        confidence = "high"
    elif ml_result["available"] or c2pa_result["present"]:
        confidence = "medium"
    else:
        confidence = "low"

    if score >= 65:
        verdict = "likely_ai"
    elif score >= 40:
        verdict = "possibly_ai"
    elif has_camera_evidence and score < 20:
        verdict = "likely_camera"
    else:
        verdict = "inconclusive"

    if not signals:
        signals.append({"label": "No strong indicators either way", "weight": 0, "tier": "info"})

    return {
        "verdict": verdict,
        "suspicion_score": score,
        "confidence": confidence,
        "signals": signals,
        "c2pa": c2pa_result,
        "ml_classifier": ml_result,
        "fft_periodicity": fft,
        "has_camera_evidence": has_camera_evidence,
        "disclaimer": (
            "Offline indicators only, not proof of AI generation. Confidence "
            f"in this score is '{confidence}' -- see individual signals above "
            "for the reasoning."
        ),
    }
