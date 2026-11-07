"""Command-line interface for pdf-extract."""

import argparse
import sys
from pathlib import Path

from pdf_extractor import poppler
from pdf_extractor.poppler import PdfError, ToolError
from pdf_extractor.snapshot import build_snapshot, write_snapshot

EXIT_OK = 0
EXIT_FILE_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-extract",
        description="Convert every PDF in a directory into a JSON text snapshot.",
    )
    parser.add_argument("input_dir", type=Path, help="directory containing the PDF files")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="directory to write the JSON files to (default: ./output)",
    )
    return parser


def find_pdfs(input_dir: Path) -> list[Path]:
    """Return the PDF files directly inside ``input_dir``, sorted by file name."""
    pdfs = (p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    return sorted(pdfs, key=lambda p: p.name)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_dir: Path = args.input_dir
    output_dir: Path = args.output

    if not input_dir.is_dir():
        reason = "does not exist" if not input_dir.exists() else "is not a directory"
        print(f"error: input path '{input_dir}' {reason}", file=sys.stderr)
        return EXIT_USAGE

    try:
        tool_version = poppler.check_tools()
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    pdfs = find_pdfs(input_dir)
    if not pdfs:
        print(f"no PDF file found in '{input_dir}'")
        return EXIT_OK

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create output directory '{output_dir}': {exc}", file=sys.stderr)
        return EXIT_USAGE

    succeeded = failed = 0
    for pdf in pdfs:
        try:
            target = write_snapshot(build_snapshot(pdf, tool_version), output_dir)
        except (PdfError, OSError) as exc:
            failed += 1
            print(f"FAIL {pdf.name}: {exc}", file=sys.stderr, flush=True)
        else:
            succeeded += 1
            print(f"OK   {pdf.name} -> {target}", flush=True)

    print(f"{succeeded} succeeded, {failed} failed")
    return EXIT_FILE_FAILED if failed else EXIT_OK
