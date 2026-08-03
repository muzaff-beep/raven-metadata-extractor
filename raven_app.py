#!/usr/bin/env python3
"""
Raven Metadata Extractor — unified entry point (GUI + CLI in one build)

- No arguments  -> launches the GUI (raven_gui.RavenApp), same as before.
- Any arguments -> runs in CLI mode, same behavior as the old raven_cli.py.

This lets the whole app ship as a SINGLE PyInstaller binary instead of two
separate GUI/CLI executables: double-click it (or run with no args) for the
GUI, or call it from a terminal/script with a folder argument for the CLI.

Examples:
    raven                                  # opens the GUI
    raven /path/to/photos                  # CLI: scan once, print summary
    raven /path/to/photos --recursive
    raven /path/to/photos -o extra.json
    raven --gui                            # force GUI even if other flags are odd
"""
from __future__ import annotations
import argparse
import json
import sys


def _run_gui() -> int:
    from raven_gui import RavenApp
    app = RavenApp()
    app.mainloop()
    return 0


def _run_cli(argv: list[str]) -> int:
    from raven import process_folder, build_summary, save_report

    parser = argparse.ArgumentParser(
        prog="raven_app",
        description="Extract image metadata + AI indicators into a timestamped JSON report. "
                    "Run with no arguments to launch the GUI instead.")
    parser.add_argument("folder", help="Folder containing image files")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument("-o", "--output", default=None,
                        help="Optional extra copy written to this exact path "
                             "(report is always also saved to RavenReports/).")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (0 = compact)")
    args = parser.parse_args(argv)

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


def main() -> int:
    argv = sys.argv[1:]

    # Explicit override: `raven --gui` always opens the GUI, even though it
    # technically has one argv item -- useful for desktop shortcuts/launchers
    # that might pass flags.
    if not argv or argv == ["--gui"]:
        return _run_gui()

    return _run_cli(argv)


if __name__ == "__main__":
    sys.exit(main())
