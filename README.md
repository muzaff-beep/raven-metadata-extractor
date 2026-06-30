# Raven Metadata Extractor

## Overview

The Raven Metadata Extractor is a Python-based command-line utility designed to extract comprehensive metadata from a collection of image files and consolidate it into a single, structured JSON array. This tool is particularly useful for photographers, digital archivists, and developers who need to programmatically access detailed information embedded within image files.

## Features

- **Multi-Source Metadata Extraction**: Merges metadata from various robust libraries, including:
    - **Pillow**: Extracts EXIF and GPS IFDs, decoding values into human-readable formats (e.g., exposure, f-stop, ISO, flash).
    - **ExifRead**: Fills in any additional tags that Pillow might miss, such as MakerNote-adjacent fields and raw lens data.
    - **XMP**: Parses Extensible Metadata Platform (XMP) data using real XML parsing, capturing information like keywords, ratings, creator details, and edit history.
- **Batch Processing**: Efficiently processes entire folders of images, with an option for recursive scanning of subdirectories.
- **Supported Formats**: Compatible with a wide range of image file types, including JPG, JPEG, PNG, TIFF, TIF, WEBP, HEIC, HEIF, BMP, and GIF.
- **Structured JSON Output**: Generates a clean, well-organized JSON output file, making it easy to integrate with other systems or for further analysis.
- **Error Handling**: Provides clear error reporting for files where metadata extraction might be partial or unsuccessful.

## Installation

To set up the Raven Metadata Extractor, follow these steps:

1.  **Install Python**: Ensure you have Python 3.10 or newer installed. You can download it from [python.org](https://www.python.org/). During installation, make sure to check the option "Add Python to PATH."

2.  **Get the Project**: Extract the `raven_metadata_extractor.zip` file to a desired location, for example, `C:\Tools\raven` on Windows or `/opt/raven` on Linux/macOS.

3.  **Install Dependencies**: Open your terminal or command prompt, navigate to the project directory, and install the required Python packages:

    ```bash
    cd C:\Tools\raven\raven_metadata_extractor  # Or your chosen path
    pip install -r requirements.txt
    ```

## Usage

The `raven_cli.py` script is the main entry point for the Raven Metadata Extractor. It allows you to process image folders and output the extracted metadata to a JSON file.

### Basic Usage

To extract metadata from a folder and save it to a JSON file:

```bash
python raven_cli.py "C:\Users\YourName\Pictures\MyFolder" -o metadata.json
```

-   Replace `"C:\Users\YourName\Pictures\MyFolder"` with the actual path to your image folder. Use quotes if the path contains spaces.
-   The `-o` or `--output` flag specifies the output JSON file name (e.g., `metadata.json`).

### Recursive Processing

To process images in subdirectories as well, use the `--recursive` flag:

```bash
python raven_cli.py "/path/to/your/image/folder" --recursive -o all_metadata.json
```

### JSON Output Indentation

You can control the indentation of the JSON output using the `--indent` flag. By default, it's set to `2`. Use `0` for compact JSON output:

```bash
python raven_cli.py "/path/to/your/image/folder" -o compact_metadata.json --indent 0
```

### Example `run.bat` for Windows (Optional)

For Windows users, you can create a `run.bat` file in the project directory to easily drag-and-drop folders for processing:

1.  Create a new file named `run.bat` in the same directory as `raven_cli.py`.
2.  Add the following content to `run.bat`:

    ```batch
    @echo off
    set /p folder="Drag folder here and press Enter: "
    python raven_cli.py "%folder%" -o metadata.json
    pause
    ```

3.  Save the file. Now, you can drag an image folder onto `run.bat`, and it will prompt you to press Enter to process it.

## Output Structure

Each image processed will result in a record within the JSON array, structured as follows:

```json
[
  {
    "file": {
      "filename": "image.jpg",
      "path": "/path/to/image.jpg",
      "size_bytes": 1234567,
      "size_human": "1.2 MB",
      "mime_type": "image/jpeg",
      "extension": "jpg",
      "modified_at": "2023-10-27T10:00:00Z",
      "created_at": "2023-10-27T09:00:00Z",
      "sha256": "a1b2c3d4e5f67890..."
    },
    "metadata": {
      "image": {
        "width": 1920,
        "height": 1080,
        "mode": "RGB",
        "format": "JPEG"
      },
      "exif": {
        "Make": "Canon",
        "Model": "Canon EOS 5D Mark IV",
        "ExposureTime": "1/250 sec",
        "FNumber": "f/4.0",
        "ISOSpeedRatings": 100,
        "DateTimeOriginal": "2023:10:27 09:30:00",
        "Flash": "Off, Did not fire"
        // ... other EXIF tags
      },
      "gps": {
        "raw": {
          "GPSLatitudeRef": "N",
          "GPSLatitude": [34, 56, 23.12],
          "GPSLongitudeRef": "W",
          "GPSLongitude": [118, 12, 45.67],
          "GPSAltitudeRef": 0,
          "GPSAltitude": 100.0
        },
        "decimal": {
          "latitude": 34.939755,
          "longitude": -118.212686,
          "altitude_m": 100.0,
          "google_maps_url": "https://www.google.com/maps?q=34.939755,-118.212686"
        }
      },
      "xmp": {
        "dc:creator": ["John Doe"],
        "dc:description": "A beautiful landscape shot.",
        "photoshop:DateCreated": "2023-10-27T09:30:00",
        "xmp:Rating": 4
        // ... other XMP fields
      }
    },
    "errors": [] // Any errors encountered during extraction for this specific file
  }
]
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues on the GitHub repository.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details (if applicable).

## Contact

For questions or support, please open an issue on the GitHub repository.

