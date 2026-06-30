# Raven Metadata Extractor

Extracts complete metadata from a folder of images into a single JSON array.

## Install
```
pip install -r requirements.txt
```

## Usage
```
python raven_cli.py /path/to/folder -o metadata.json
python raven_cli.py /path/to/folder --recursive
```

## Sources merged per image
- **Pillow** — EXIF + GPS IFDs, decoded to human-readable values (exposure, f-stop, ISO, flash, etc.)
- **exifread** — fills any tags Pillow misses (MakerNote-adjacent fields, raw lens data)
- **XMP** — parsed with real XML (not regex): keywords, ratings, creator, edit history

## Output shape (per image)
```json
{
  "file": { "filename", "path", "size_bytes", "size_human", "mime_type", "extension", "modified_at", "created_at", "sha256" },
  "metadata": {
    "image": { "width", "height", "mode", "format" },
    "exif": { "...decoded tag: value pairs..." },
    "gps": { "raw": {...}, "decimal": { "latitude", "longitude", "altitude_m", "google_maps_url" } },
    "xmp": { "...fields..." } 
  },
  "errors": ["..."]
}
```
Supported: jpg, jpeg, png, tiff, tif, webp, heic, heif, bmp, gif.
