# Raven Metadata Extractor

Cross-platform (Windows / macOS / Linux) desktop app + CLI that scans a folder
of images and produces a comprehensive, timestamped JSON metadata report —
including offline AI-generation indicators.

## Features
- **2-tab GUI**: Scan, History — native look on Windows, macOS, and Linux
- **Multi-source extraction**: Pillow (EXIF/GPS) + exifread (extra tags) + native
  XMP via `Image.getxmp()` (works across JPEG/PNG/TIFF, not just JPEG)
- **Scan tab — single-screen workflow**:
  - Folder picker + live scrolling scan log on the left (per-file progress,
    flagged AI verdicts as they're found)
  - Dashboard cards (Images / GPS / AI Flags / Cameras / C2PA) across the top
  - Filter dropdown (All / Likely AI / Possibly AI / Camera / Has GPS / No GPS
    / Has C2PA) + live search + **paginated results table** (10 per page)
  - **Double-click any row** to open the detail modal: image preview,
    colorized profile pills (camera / resolution / GPS / C2PA validity),
    side-by-side GPS-info and AI-probability cards, and a **tabbed panel**
    (EXIF / XMP / C2PA / Raw JSON) for full drilldown
- **History tab**: every saved report, double-click to reload it back into
  the Scan tab's dashboard/table/console (without re-scanning)
- **Comprehensive summary report** per scan:
  - Camera / lens breakdown (counts per make/model)
  - GPS map links + location clustering
  - Date range / shot timeline
  - Format / size / resolution / megapixel stats
  - Missing-metadata & anomaly flags
  - **AI-generation indicators** (see below)
- **Report storage**: every scan auto-saves to `Documents/RavenReports/`
  (or `~/RavenReports/` if no Documents folder exists) as
  `<foldername>_<YYYY-MM-DD_HH-MM-SS>.json`
- **History tab**: lists every saved report with source folder, name, timestamp, image count

## AI-generation indicators — how the score actually works

> **This is an indicator, never proof.** No offline heuristic and no
> lightweight bundled model can definitively determine whether an image was
> AI-generated, especially against modern diffusion models. Treat the score
> as a signal to guide human review, not a verdict.

The score is built from **tiered, weighted evidence** — not arbitrary
point-summing — so one strong signal can settle the verdict, and weak signals
can only nudge an otherwise-ambiguous score:

| Tier | Signal | Notes |
|---|---|---|
| Strong | **C2PA / Content Credentials manifest** | Reads the actual IPTC `digitalSourceType` field (e.g. `trainedAlgorithmicMedia` vs `digitalCapture`) via the official `c2pa-python` SDK — a cryptographically-signed, standardized claim, not a guess. *Optional dependency.* |
| Strong | **AI tool name in metadata** | e.g. `Software: Midjourney v6` |
| Moderate | **Local ML classifier** | Optional ONNX model signal. Honestly scoped: most publicly available lightweight models are *face-deepfake* detectors, not general AI-art detectors, with modest published accuracy — weighted accordingly, never decisive alone. *Optional dependency, requires you to supply a model file.* |
| Moderate | **Camera-capture EXIF present** | Pushes score down — real evidence of a capture device |
| Weak | **No camera EXIF** | Only weighted lightly, and **only when there's no explanation for it**. If the image bears a known platform re-encode fingerprint (WhatsApp, Instagram, Discord, etc. — which strip EXIF from nearly every real photo that passes through them), this contributes **nothing**, since it's not evidence of AI origin. |
| Weak | **FFT frequency-domain periodicity** | Catches older GAN/upscaler artifacts; largely absent in modern diffusion model (SDXL, Flux, Midjourney v6+) output, so treated as a minor, dated signal |

Every signal that fires — its label, its weight, and its tier — is shown in
the detail modal. The score is never presented as a bare, unexplained
percentage.

### Enabling the optional signals
```
pip install -r requirements-optional.txt
```
- **`c2pa-python`** — enables real manifest parsing. Works immediately, no
  further setup; if a file has no manifest it's simply skipped (not an error).
- **`onnxruntime`** — enables the local ML classifier signal, but you must
  also supply a model file (this repo doesn't bundle one). Point
  `RAVEN_AI_CLASSIFIER_MODEL` at your `.onnx` file, or drop it at
  `raven/models/ai_image_classifier.onnx`. **Verify your model's input size,
  normalization, and output class ordering** against the defaults in
  `raven/ml_classifier.py` — override via `RAVEN_AI_CLASSIFIER_INPUT_SIZE`,
  `RAVEN_AI_CLASSIFIER_MEAN`, `RAVEN_AI_CLASSIFIER_STD`,
  `RAVEN_AI_CLASSIFIER_AI_CLASS_INDEX` env vars if they differ. A wrong
  assumption here produces a confident-looking but meaningless number.

Both are fully optional — the app works identically without them, just
without those specific signals contributing to the score.

## Install (from source)
```
pip install -r requirements.txt
# optional, for stronger AI-detection signals:
pip install -r requirements-optional.txt
```

## Run the GUI
```
python raven_gui.py
```
Pick a folder → Start Scan → results appear live in the dashboard/table on the
right as each image is processed → double-click any row for full details.

## Run the CLI
```
python raven_cli.py /path/to/images
python raven_cli.py /path/to/images --recursive
python raven_cli.py /path/to/images -o extra_copy.json
```
Reports always save to `Documents/RavenReports/` regardless; `-o` writes an extra copy.

## Building binaries
Cross-platform builds run automatically via GitHub Actions
(`.github/workflows/build.yml`) on push to `main`/`master`, on pull requests,
and on `v*` tags (which also publishes a GitHub Release with every OS's
binaries attached). Matrix covers Windows, macOS, and Linux, building both
the GUI and CLI as standalone binaries.

To build locally:
```
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name RavenExtractor --collect-all PIL --collect-all exifread --collect-all numpy raven_gui.py
pyinstaller --onefile --console --name raven-cli --collect-all PIL --collect-all exifread --collect-all numpy raven_cli.py
```

## Report structure
```
{
  "summary": { totals, camera_breakdown, lens_breakdown, format_stats,
               size_stats, date_range, gps{clusters}, anomalies, ai_indicators },
  "records": [
    {
      "file": { filename, path, size_human, created_at, modified_at, ... },
      "metadata": {
        "image": { width, height, format, mode },
        "exif": { ... },
        "gps": { decimal: { latitude, longitude, altitude_m, google_maps_url } },
        "xmp": { ... },
        "ai_indicators": {
          "verdict": "likely_ai" | "possibly_ai" | "likely_camera" | "inconclusive",
          "suspicion_score": 0-100,
          "confidence": "low" | "medium" | "high",
          "signals": [ { "label": str, "weight": int, "tier": str }, ... ],
          "c2pa": { present, valid, claim_generator, software_agents, digital_source_types, ai_generated },
          "ml_classifier": { available, ai_probability, scope },
          "fft_periodicity": float | null,
          "disclaimer": str
        }
      },
      "errors": []
    }
  ]
}
```

## Supported formats
jpg, jpeg, png, tiff, tif, webp, heic, heif, bmp, gif

## Platform notes
- **Visual design**: cards, pills, and buttons use true rounded corners drawn
  on Canvas (`raven_widgets.py`), not stock Tkinter's hard-edged Frame/Button.
  Icons (`raven_icons.py`) are small vector line-icons drawn directly on
  Canvas in a Lucide-style stroke aesthetic — no bundled image files, no icon
  font, no extra dependency.
- **Fonts**: the GUI auto-detects installed fonts per OS (Segoe UI / SF Pro /
  Ubuntu / DejaVu Sans, with generic Tk fallbacks) rather than hardcoding
  Windows-only font names.
- **"Open Reports Folder"** uses the native file manager per OS (`explorer`
  on Windows, `open` on macOS, `xdg-open` on Linux).
- **Linux GUI builds** need `python3-tk` installed (handled automatically in
  CI; install manually via your package manager for local builds).
