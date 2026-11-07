# Proposal

## Why

We want to pull a few key financial figures (valuation, performance, income…) out of PDF statements from several issuers, deterministically and with no AI at run time. Extraction rules are much easier to write, test and debug against plain text than against PDFs, so the first step is a stable, issuer-independent stage that turns each PDF into a self-describing text snapshot. Rule-based figure extraction (stage 2) will build on that snapshot in a later change.

## What Changes

- New Python command-line tool that takes a directory, finds every PDF directly inside it, and converts each one to text using poppler's `pdftotext` in **layout mode**.
- For each PDF, writes one JSON document containing:
  - the raw layout text, split per page;
  - source metadata: file name, SHA-256 of the file, page count;
  - extraction metadata: extraction datetime (UTC), tool name, tool (poppler) version, mode.
- Clear failure behaviour: a missing `pdftotext` binary stops the run; a bad PDF or a PDF without a text layer (scanned) is reported and skipped while the other files are still processed; the exit code reflects whether any file failed.
- Project scaffolding: Python package, test suite, `.gitignore` that keeps real statements (personal data) and generated output out of version control.

Out of scope: extracting specific figures, rule/template files, OCR for scanned PDFs, recursive directory scanning, CSV/database outputs, de-duplication across runs.

## Capabilities

### New Capabilities
- `pdf-text-extraction`: Converting a directory of PDF documents into per-document JSON text snapshots (layout-mode text per page plus source and extraction metadata), including how failures are reported.

### Modified Capabilities

_None. This is the first capability in the project._

## Impact

- New code: a Python package with a CLI entry point, and tests. The project currently holds only OpenSpec scaffolding and sample PDFs.
- New runtime dependency: the system binaries `pdftotext` and `pdfinfo` (poppler-utils, verified locally at 24.02.0). The Python side uses the standard library only; `pytest` is a development dependency.
- Data handling: the sample PDFs in `pdfs/` contain personal account data and must not be committed; tests use synthetic fixtures instead.
