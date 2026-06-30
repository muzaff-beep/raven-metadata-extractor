#!/usr/bin/env python3
"""
Raven Metadata Extractor — CLI

Usage:
    python -m raven_cli <folder> [-o output.json] [--recursive] [--indent N]
"""
from __future__ import annotations
import argparse
import json
import sys

from raven import process_folder


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract complete image metadata from a folder into one JSON array.")
    parser.add_argument("folder", help="Folder containing image files")
    parser.add_argument("-o", "--output", default="metadata.json", help="Output JSON file (default: metadata.json)")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (default: 2, use 0 for compact)")
    args = parser.parse_args()

    try:
        results = process_folder(args.folder, recursive=args.recursive)
    except NotADirectoryError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not results:
        print(f"No supported image files found in: {args.folder}", file=sys.stderr)

    indent = args.indent if args.indent > 0 else None
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=indent, ensure_ascii=False, default=str)

    error_count = sum(1 for r in results if r.get("errors"))
    print(f"Processed {len(results)} image(s) -> {args.output}")
    if error_count:
        print(f"{error_count} file(s) had partial extraction errors (see 'errors' field per record).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
