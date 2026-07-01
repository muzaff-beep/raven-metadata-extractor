#!/usr/bin/env python3
"""
Raven Metadata Extractor — CLI

Scans a folder, builds a comprehensive summary + AI-generation indicators,
and saves a timestamped report to Documents/RavenReports/.

Usage:
    python raven_cli.py <folder> [--recursive] [-o custom_output.json]
"""
from __future__ import annotations
import argparse
import json
import sys

from raven import process_folder, build_summary, save_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract image metadata + AI indicators into a timestamped JSON report.")
    parser.add_argument("folder", help="Folder containing image files")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument("-o", "--output", default=None,
                        help="Optional extra copy written to this exact path (report is always also saved to RavenReports/).")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (0 = compact)")
    args = parser.parse_args()

    try:
        records = process_folder(args.folder, recursive=args.recursive)
    except NotADirectoryError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    summary = build_summary(records, args.folder)
    entry = save_report(records, summary, args.folder)

    n = summary["totals"]["images_scanned"]
    ai = summary["ai_indicators"]
    print(f"Scanned {n} image(s).")
    print(f"Report saved: {entry['report_path']}")
    print(f"AI indicators: {ai['likely_ai_count']} likely, {ai['possibly_ai_count']} possibly AI-generated.")

    if args.output:
        indent = args.indent if args.indent > 0 else None
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "records": records}, f,
                      indent=indent, ensure_ascii=False, default=str)
        print(f"Extra copy written: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
