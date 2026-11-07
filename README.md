# pdf-extractor

Deterministic extraction of data from financial PDF statements. No AI or LLM is involved at run time.

The current stage converts each PDF into a JSON **text snapshot**: the `pdftotext -layout` output of every page, plus metadata about the source file and the extraction. Rules that extract specific figures from these snapshots will come in a later stage.

## Prerequisites

- Python 3.12 or newer
- poppler-utils (`pdftotext` and `pdfinfo`) on the `PATH`:

  ```sh
  sudo apt install poppler-utils      # Debian / Ubuntu
  brew install poppler                # macOS
  ```

## Installation

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Usage

```sh
.venv/bin/pdf-extract <input_dir> [-o OUTPUT_DIR]
```

- Every file ending in `.pdf` (any case) directly inside `input_dir` is processed, in file-name order. Subdirectories are not scanned.
- One JSON file per PDF is written to `OUTPUT_DIR` (default `./output`, created if needed), named after the PDF: `statement.pdf` → `statement.pdf.json`. Existing files are overwritten.
- A PDF that cannot be processed (corrupt, or no text layer, as with scanned documents) is reported on stderr and skipped; the other files are still processed.

Example:

```console
$ .venv/bin/pdf-extract pdfs/ -o output/
OK   2025-12-31_statement.pdf -> output/2025-12-31_statement.pdf.json
FAIL scanned.pdf: no text layer found (scanned or image-only PDF?)
1 succeeded, 1 failed
```

`python -m pdf_extractor` works as well.

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Every PDF was converted, or the directory contains no PDF |
| `1`  | At least one PDF failed; the others were converted |
| `2`  | Usage or environment error: input directory missing or not a directory, poppler-utils missing, output directory cannot be created. Nothing is written |

## Output format

```json
{
  "schema_version": 1,
  "source": {
    "file_name": "statement.pdf",
    "sha256": "9f2c…",
    "page_count": 22
  },
  "extraction": {
    "extracted_at": "2026-11-07T09:42:13Z",
    "tool": "pdftotext",
    "tool_version": "24.02.0",
    "mode": "layout"
  },
  "pages": [
    "RELEVÉ DE PORTEFEUILLE\nSITUATION AU 31/01/2026\n…",
    "…"
  ]
}
```

| Field | Description |
|-------|-------------|
| `schema_version` | Version of this format, currently `1` |
| `source.file_name` | Base name of the PDF (no directory) |
| `source.sha256` | SHA-256 of the PDF bytes. Identical files share it whatever their name |
| `source.page_count` | Page count reported by `pdfinfo` |
| `extraction.extracted_at` | When the file was processed, ISO 8601 UTC |
| `extraction.tool_version` | poppler version used. Layout spacing can differ between versions |
| `pages` | One string per page, exactly as produced by `pdftotext -layout` |

Running the tool twice on the same PDF with the same poppler version gives files that differ only in `extracted_at`.

## Development

```sh
.venv/bin/pytest            # tests use synthetic PDFs; poppler tests are skipped if it is missing
.venv/bin/ruff check .
.venv/bin/ruff format .
```

Real statements contain personal data: keep them in `pdfs/` (git-ignored). Generated snapshots go to `output/`, which is git-ignored too.
