# Design

## Context

The repository is greenfield: only OpenSpec scaffolding and a `pdfs/` folder of sample statements (portfolio reports from a wealth-management firm, with an embedded Unicode text layer). Exploration showed that `pdftotext -layout` gives clean, row-preserving text for these files. Locally available: Python 3.12.3 and poppler-utils 24.02.0 (`pdftotext`, `pdfinfo`). See proposal.md for motivation and scope; see `specs/pdf-text-extraction/spec.md` for the behaviour contract.

## Goals / Non-Goals

**Goals:**
- A small, dependency-free (standard library) Python package with a CLI.
- Output that is byte-stable for a given PDF and poppler version (apart from the timestamp), so stage 2 rules and their tests can rely on it.
- Tests that run without the personal sample PDFs.

**Non-Goals:**
- Any wrapper around pdftotext options other than layout mode (no raw mode, no page ranges, no cropping).
- Parallel processing. Volumes are a handful of statements per run.
- Packaging and distribution beyond a local editable install.

## Decisions

### D1. Call poppler binaries through `subprocess` rather than a Python PDF library
`pdftotext -layout -enc UTF-8 <file> -` writes the text to stdout; `pdfinfo <file>` gives `Pages:`. Alternatives: pypdf / pdfminer / pdfplumber. These produce *different* text layouts, would add pip dependencies, and the exploration was done on pdftotext output. Poppler is the most widely used, predictable extractor, and its version is easy to record. Commands are run with an argument list (never `shell=True`), with a timeout (60 s per call). A timeout counts as a per-file failure.

### D2. Page splitting and its integrity check
pdftotext separates pages with `\f` and ends its output with a final `\f`. Strip exactly one trailing `\f`, then split on `\f`. The resulting count must equal `pdfinfo`'s `Pages:`. A mismatch is a per-file failure rather than a silently wrong snapshot. Page text is otherwise left untouched: no trimming, no line-ending normalisation.

### D3. Page count from `pdfinfo`, not from the split
Using a second, independent source turns the split into a verified result (see D2). `pdfinfo` also gives the earliest, cheapest signal for corrupt files: a non-zero exit means the file failed.

### D4. Tool version detection
Run `pdftotext -v` once per run. Poppler prints `pdftotext version X.Y.Z` on **stderr**, so stdout and stderr are both searched with `pdftotext version (\S+)`. If neither binary is found, or the version cannot be parsed, the run fails up front (exit 2) and nothing is written. An `"unknown"` value would weaken the snapshot's provenance.

### D5. Output naming `<file name>.json`
`statement.pdf` produces `statement.pdf.json`, rather than `statement.json`. Keeping the full name avoids collisions between `a.pdf` and `a.PDF`, or a PDF and a same-stem file, and maps back to the source unambiguously.

### D6. JSON serialisation
`json.dumps(..., ensure_ascii=False, indent=2)` with a fixed key order (schema_version, source, extraction, pages) and a trailing newline, written as UTF-8. `ensure_ascii=False` keeps `€` and `É` readable when a person (or the stage 2 AI setup skill) opens the file. Each file is written to a temporary file in the output directory, then moved into place with `os.replace`, so an interrupted run never leaves a truncated JSON.

### D7. Exit codes
`0`: all PDFs succeeded, or there were no PDFs. `1`: at least one PDF failed. `2`: usage or environment error (bad input directory, missing or unusable poppler). Scripts and cron jobs can then tell "fix the setup" apart from "check a file".

### D8. Package layout and entry point
```
pyproject.toml               # [project.scripts] pdf-extract = "pdf_extractor.cli:main"
src/pdf_extractor/
    __init__.py
    __main__.py              # python -m pdf_extractor
    poppler.py               # tool discovery, version, pdfinfo, pdftotext calls
    snapshot.py              # build the JSON document for one PDF (sha256, pages, metadata)
    cli.py                   # argparse, directory scan, per-file loop, summary, exit codes
tests/
```
`src/` layout with argparse. The CLI is `pdf-extract <input_dir> [-o OUTPUT]`. The SHA-256 is computed by streaming the file in chunks.

### D9. Test fixtures are synthetic
The real statements contain personal account data and stay out of git (`pdfs/` and `output/` in `.gitignore`). A test helper writes minimal valid PDFs (standard Type1 Helvetica text, multi-page, plus a page with no text) using only the standard library. Corrupt fixtures are arbitrary bytes. Tests that need poppler are skipped with a clear reason when it isn't installed. Tool-absence and version-parsing paths are unit-tested by stubbing the subprocess layer.

## Risks / Trade-offs

- [Layout text spacing can change between poppler versions] → `tool_version` is recorded in every snapshot. Stage 2 rules should match whitespace with `\s+`, not exact space counts.
- [System dependency not installable via pip] → Fail fast with an explicit "install poppler-utils" message (exit 2). Document it in the README.
- [Side-by-side blocks interleave in layout mode (seen on page 2 of the samples)] → Accepted for this change. A per-template mode choice can come with stage 2 if needed.
- [Scanned PDFs yield nothing] → Detected and reported as a failure (no text layer). OCR is out of scope.
- [Large snapshot files (≈ 800 lines of padded text per 20-page statement)] → Acceptable at current volumes.
