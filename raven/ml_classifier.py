"""
Optional local ML signal for AI-image suspicion, using an ONNX Runtime session
with a small pretrained image classifier.

HONEST SCOPING (read before trusting this too much):
  - Publicly available lightweight pretrained detectors are overwhelmingly
    trained for *face deepfake / face-swap* detection, not general
    "is this whole image AI-generated" classification. A landscape, product
    photo, or AI-generated illustration is largely out of scope for them.
  - Published accuracy on these models is modest and asymmetric (e.g. the
    prithivMLmods/Deep-Fake-Detector line reports ~70% overall accuracy with
    the "Fake" class recall around 0.4-0.5 on its own validation set) — meaning
    it misses a large fraction of real fakes and should never stand alone.
  - Detector generalization to newer generators (Midjourney v6+, FLUX, SDXL)
    is an open research problem; a model trained on older GAN/diffusion
    outputs can silently fail on the latest tools.
  - Because of the above, this module NEVER returns a bare "this is AI"
    verdict. It returns a raw probability plus an explicit scope/confidence
    flag, and the caller (ai_detect.py) treats it as one weighted signal
    among several, capped so it can't dominate the final score alone.

This is entirely optional: if onnxruntime or the model file isn't available,
every function degrades to returning {"available": False}.
"""
from __future__ import annotations
import os
from typing import Optional

_MODEL_ENV_VAR = "RAVEN_AI_CLASSIFIER_MODEL"
_DEFAULT_MODEL_REL_PATH = os.path.join(os.path.dirname(__file__), "models", "ai_image_classifier.onnx")

try:
    import onnxruntime as ort
    import numpy as np
    _ORT_AVAILABLE = True
except ImportError:
    _ORT_AVAILABLE = False

_session = None
_session_load_attempted = False


def _model_path() -> Optional[str]:
    p = os.environ.get(_MODEL_ENV_VAR) or _DEFAULT_MODEL_REL_PATH
    return p if os.path.isfile(p) else None


def is_available() -> bool:
    return _ORT_AVAILABLE and _model_path() is not None


def _get_session():
    global _session, _session_load_attempted
    if _session is not None or _session_load_attempted:
        return _session
    _session_load_attempted = True
    if not _ORT_AVAILABLE:
        return None
    path = _model_path()
    if not path:
        return None
    try:
        _session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    except Exception:
        _session = None
    return _session


_INPUT_SIZE = int(os.environ.get("RAVEN_AI_CLASSIFIER_INPUT_SIZE", "224"))
_AI_CLASS_INDEX = int(os.environ.get("RAVEN_AI_CLASSIFIER_AI_CLASS_INDEX", "1"))
# ImageNet normalization is the common default for ViT/CNN classifiers, but is
# NOT universal -- override via env vars if your model's preprocessing differs.
_NORM_MEAN = tuple(float(x) for x in os.environ.get("RAVEN_AI_CLASSIFIER_MEAN", "0.485,0.456,0.406").split(","))
_NORM_STD = tuple(float(x) for x in os.environ.get("RAVEN_AI_CLASSIFIER_STD", "0.229,0.224,0.225").split(","))


def classify_image(path: str) -> dict:
    """
    Returns:
        {
          "available": bool,
          "ai_probability": float | None,   # 0..1, model's raw output
          "scope": str,                     # what the model was actually trained for
          "error": str | None,
        }

    "available" being False (no onnxruntime, or no model file bundled/configured)
    is the normal, expected case out of the box — this is an opt-in extra a
    user can enable by installing onnxruntime and pointing
    RAVEN_AI_CLASSIFIER_MODEL at a model file, or dropping one in
    raven/models/ai_image_classifier.onnx.

    IMPORTANT: input size, normalization stats, and which output index means
    "AI/fake" are all MODEL-SPECIFIC and cannot be safely assumed for an
    arbitrary bundled model. Defaults here (224x224, ImageNet mean/std, class
    index 1) match common ViT deepfake-classifier conventions, but you MUST
    verify these against whatever model you actually plug in -- override via
    RAVEN_AI_CLASSIFIER_INPUT_SIZE / _MEAN / _STD / _AI_CLASS_INDEX env vars
    if they differ. Getting this wrong silently produces a confident-looking
    but meaningless number, which is worse than not having the signal at all.
    """
    result = {
        "available": False,
        "ai_probability": None,
        "scope": "face-deepfake classifier (ViT, 224x224) — not a general AI-art detector",
        "error": None,
    }
    session = _get_session()
    if session is None:
        return result

    try:
        from PIL import Image
        with Image.open(path) as img:
            img = img.convert("RGB").resize((_INPUT_SIZE, _INPUT_SIZE))
            arr = np.asarray(img, dtype=np.float32) / 255.0
            mean = np.array(_NORM_MEAN, dtype=np.float32)
            std = np.array(_NORM_STD, dtype=np.float32)
            arr = (arr - mean) / std
            arr = arr.transpose(2, 0, 1)[None, ...]  # NCHW

        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: arr})
        logits = np.asarray(outputs[0]).reshape(-1)

        if logits.size < 2:
            # Single-logit sigmoid-style output, not a 2-class softmax
            ai_prob = float(1.0 / (1.0 + np.exp(-logits[0])))
        else:
            exp = np.exp(logits - np.max(logits))
            probs = exp / exp.sum()
            idx = _AI_CLASS_INDEX if _AI_CLASS_INDEX < len(probs) else len(probs) - 1
            ai_prob = float(probs[idx])

        result["available"] = True
        result["ai_probability"] = round(ai_prob, 4)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result
