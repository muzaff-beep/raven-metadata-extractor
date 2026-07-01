# Raven Metadata Extractor

Desktop app (Windows GUI) + CLI that scans a folder of images and produces a
comprehensive, timestamped JSON metadata report — including offline
AI-generation indicators.

## Features
- **3-tab GUI**: Scan, History, Reader
- **Multi-source extraction**: Pillow (EXIF/GPS) + exifread (extra tags) + XMP (real XML parsing)
- **Comprehensive summary report** per scan:
  - Camera / lens breakdown (counts per make/model)
  - GPS map links + location clustering
  - Date range / shot timeline
  - Format / size / resolution / megapixel stats
  - Missing-metadata & anomaly flags
  - **AI-generation indicators** (offline): metadata heuristics, C2PA / Content
    Credentials detection, and an FFT frequency-domain periodicity score
- **Report storage**: every scan auto-saves to `Documents/RavenReports/`
  as `<foldername>_<YYYY-MM-DD_HH-MM-SS>.json` (flat, no subfolders)
- **History tab**: lists every saved report with source folder location, name, timestamp, image count
- **Reader tab**: dashboard cards + searchable image table + per-image JSON drilldown

> **AI detection is indicator-only, never proof.** Offline heuristics cannot
> definitively determine AI generation; the score guides human review.

## Install (from source)
```
pip install -r requirements.txt
```

## Run the GUI
```
python raven_gui.py
```
Pick a folder → Extract → report saves automatically → view in Reader/History.

## Run the CLI
```
python raven_cli.py "C:\path\to\images"
python raven_cli.py "C:\path\to\images" --recursive
python raven_cli.py "C:\path\to\images" -o extra_copy.json
```
Reports always save to `Documents/RavenReports/` regardless; `-o` writes an extra copy.

## Build a Windows .exe
Handled automatically by GitHub Actions on push to `main`/`master`
(`.github/workflows/build.yml`). Download `RavenExtractor.exe` from the
run's **Artifacts**. To build locally on Windows:
```
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name RavenExtractor --collect-all numpy raven_gui.py
```

## Report structure
```
{
  "summary": { totals, camera_breakdown, lens_breakdown, format_stats,
               size_stats, date_range, gps{clusters}, anomalies, ai_indicators },
  "records": [ { file, metadata{image, exif, gps, xmp, ai_indicators}, errors } ]
}
```

## Supported formats
jpg, jpeg, png, tiff, tif, webp, heic, heif, bmp, gif
