# Spec Delta

## Purpose

Turns PDF documents into self-describing JSON text snapshots, produced in a deterministic and issuer-independent way, so that later rule-based extraction can work on plain text instead of PDFs.

## ADDED Requirements

### Requirement: Directory input
The CLI SHALL accept one input directory and process every regular file directly inside it whose extension is `.pdf`, case-insensitively. Subdirectories SHALL NOT be scanned. Files SHALL be processed in ascending order of file name.

#### Scenario: PDFs in the directory are processed
- **WHEN** the input directory contains `a.pdf`, `B.PDF` and `notes.txt`
- **THEN** `B.PDF` and `a.pdf` are processed, in file-name order, and `notes.txt` is ignored

#### Scenario: Subdirectories are not scanned
- **WHEN** the input directory contains a subdirectory `old/` holding `c.pdf`
- **THEN** `c.pdf` is not processed

#### Scenario: Directory without PDFs
- **WHEN** the input directory contains no PDF file
- **THEN** the CLI reports that no PDF was found and exits with code 0 without writing any file

### Requirement: Invalid input directory
The CLI SHALL exit with code 2 and an error message on standard error, without processing anything, when the input path does not exist or is not a directory.

#### Scenario: Missing directory
- **WHEN** the CLI is run with a path that does not exist
- **THEN** it prints an error naming the path to standard error and exits with code 2

### Requirement: One JSON file per PDF
For each successfully processed PDF, the CLI SHALL write one UTF-8 JSON file named `<pdf file name>.json` in the output directory. The output directory SHALL default to `./output`, SHALL be selectable with `-o/--output`, and SHALL be created if missing. An existing output file with the same name SHALL be overwritten.

#### Scenario: Default output location
- **WHEN** the CLI processes `statement.pdf` with no output option
- **THEN** it writes `./output/statement.pdf.json`, creating `./output` if needed

#### Scenario: Custom output directory
- **WHEN** the CLI is run with `-o /tmp/out` on a directory containing `statement.pdf`
- **THEN** it writes `/tmp/out/statement.pdf.json`

#### Scenario: Re-running overwrites
- **WHEN** `statement.pdf.json` already exists in the output directory and the CLI processes `statement.pdf` again
- **THEN** the file is replaced with the new result

### Requirement: JSON document structure
Each output JSON document SHALL contain `schema_version` (integer, `1`), a `source` object with `file_name`, `sha256` and `page_count`, an `extraction` object with `extracted_at`, `tool`, `tool_version` and `mode`, and a `pages` array of strings.

#### Scenario: Document fields
- **WHEN** a PDF is processed successfully
- **THEN** its JSON has `schema_version` 1, `source.file_name` equal to the PDF's base name without any directory, `source.sha256` equal to the lowercase hex SHA-256 of the PDF bytes, `source.page_count` equal to the PDF's page count, `extraction.tool` equal to `pdftotext` and `extraction.mode` equal to `layout`

### Requirement: Layout-mode text per page
The `pages` array SHALL hold the text produced by `pdftotext` in layout mode, with one entry per PDF page in page order and the text kept exactly as produced. The number of entries SHALL equal `source.page_count`.

#### Scenario: Page split
- **WHEN** a 3-page PDF is processed
- **THEN** `pages` has 3 entries, and entry 2 holds the layout text of page 2 only

#### Scenario: Text preserved
- **WHEN** a page contains the line `TOTAL      12 345,67 €`
- **THEN** that page's entry contains the line with its spacing and characters unchanged

### Requirement: Extraction timestamp
`extraction.extracted_at` SHALL be the time the PDF was processed, as an ISO 8601 UTC timestamp with second precision and a `Z` suffix.

#### Scenario: Timestamp format
- **WHEN** a PDF is processed
- **THEN** `extraction.extracted_at` matches `YYYY-MM-DDTHH:MM:SSZ`

### Requirement: Tool version
`extraction.tool_version` SHALL be the version number reported by the installed `pdftotext` (the poppler version), for example `24.02.0`.

#### Scenario: Version recorded
- **WHEN** the installed `pdftotext` reports `pdftotext version 24.02.0`
- **THEN** every JSON written in that run has `extraction.tool_version` equal to `24.02.0`

### Requirement: Missing or unusable extraction tool
The CLI SHALL check before processing any file that `pdftotext` and `pdfinfo` are available and that the `pdftotext` version can be determined. Otherwise, it SHALL exit with code 2 and an error message without writing any file.

#### Scenario: pdftotext not installed
- **WHEN** `pdftotext` cannot be found on the PATH
- **THEN** the CLI prints an error saying poppler-utils is required and exits with code 2

### Requirement: Per-file failure isolation
When a PDF cannot be processed, the CLI SHALL report the file name and reason on standard error, SHALL NOT write a JSON for that file, SHALL continue with the remaining PDFs, and SHALL exit with code 1 at the end. A run where every PDF succeeds SHALL exit with code 0.

#### Scenario: Corrupt PDF among valid ones
- **WHEN** the directory contains `good.pdf` and a corrupt `bad.pdf`
- **THEN** `good.pdf.json` is written, no `bad.pdf.json` is written, an error naming `bad.pdf` is printed, and the exit code is 1

### Requirement: PDF without text layer
A PDF whose extracted text is empty or contains only whitespace on every page SHALL be treated as a failed file with a reason stating that no text layer was found.

#### Scenario: Scanned PDF
- **WHEN** a PDF contains only images and no text
- **THEN** no JSON is written for it, the reported reason mentions the missing text layer, and the exit code is 1

### Requirement: Deterministic output
Processing the same PDF with the same `pdftotext` version SHALL produce JSON documents that are identical except for `extraction.extracted_at`.

#### Scenario: Two runs
- **WHEN** the same PDF is processed twice with the same tool version
- **THEN** the two JSON documents differ only in `extraction.extracted_at`

### Requirement: Run summary
The CLI SHALL print one line per processed PDF giving its outcome (output path or error), followed by a final count of succeeded and failed files.

#### Scenario: Summary
- **WHEN** a run processes 3 PDFs of which 1 fails
- **THEN** the output ends with a summary reporting 2 succeeded and 1 failed
