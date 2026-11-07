# Tasks

## 1. Project scaffolding

- [x] 1.1 Add `pyproject.toml` (Python ≥ 3.12, no runtime dependencies, dev extras `pytest` and `ruff`, console script `pdf-extract = "pdf_extractor.cli:main"`) and the empty `src/pdf_extractor/` package with `__init__.py` and `__main__.py`; verify `pip install -e '.[dev]'` succeeds and `python -m pdf_extractor --help` runs
- [x] 1.2 Add `.gitignore` covering `pdfs/`, `output/`, virtualenvs and Python caches; verify `git status` does not list the sample PDFs

## 2. Poppler integration

- [ ] 2.1 Implement tool discovery and version detection in `poppler.py` (both binaries on PATH, `pdftotext -v` parsed from stdout or stderr, error when missing or unparsable); verify with unit tests that stub the subprocess layer for found / missing / unparsable cases
- [ ] 2.2 Implement the `pdfinfo` page-count call and the `pdftotext -layout -enc UTF-8 <file> -` call, both with argument lists and a 60 s timeout, raising a per-file error on non-zero exit or timeout; verify with unit tests for success, non-zero exit and timeout
- [ ] 2.3 Add a test helper that writes synthetic PDFs (multi-page text, a text-less page or file, corrupt bytes) using only the standard library; verify the generated files open with `pdfinfo` and that a known line comes back from `pdftotext -layout`

## 3. Snapshot building

- [ ] 3.1 Implement page splitting (strip one trailing `\f`, split on `\f`, check the count against `pdfinfo`) and no-text-layer detection in `snapshot.py`; verify with unit tests covering a trailing form feed, an empty middle page, a count mismatch and whitespace-only text
- [ ] 3.2 Build the snapshot document (`schema_version`, `source` with base name / streamed SHA-256 / page count, `extraction` with UTC `...Z` timestamp / tool / version / `layout`, `pages`) in the fixed key order; verify with tests asserting every field from the "JSON document structure", "Extraction timestamp" and "Tool version" requirements
- [ ] 3.3 Implement atomic JSON writing (UTF-8, `ensure_ascii=False`, indent 2, trailing newline, temp file then `os.replace`) to `<file name>.json`; verify with tests that `€` is stored unescaped, that re-writing overwrites, and that two runs on the same PDF differ only in `extracted_at`

## 4. CLI

- [ ] 4.1 Implement `cli.py`: argparse (`input_dir`, `-o/--output` defaulting to `./output`), validating the input directory (exit 2), checking the tools up front (exit 2), and a sorted, non-recursive, case-insensitive `.pdf` scan; verify with tests for a missing directory, a file passed instead of a directory, mixed-case extensions, an ignored subdirectory and an empty directory (exit 0)
- [ ] 4.2 Implement the per-file loop with failure isolation, the per-file outcome lines, the final succeeded/failed summary, and exit codes 0/1; verify with an end-to-end test on a directory containing a good, a corrupt and a text-less PDF (exit 1, only the good JSON written, both failures named on stderr)
- [ ] 4.3 Write `README.md` covering the poppler-utils prerequisite, installation, CLI usage, the output JSON format with an example, and the exit codes; verify that the documented commands run as written against a synthetic fixture directory

## 5. Integration check

- [ ] 5.1 Run `pdf-extract pdfs/` on the real sample statements and confirm one JSON file is written per sample with `page_count` matching `pdfinfo`, that byte-identical copies share one `sha256`, and that the summary page holds the valuation figure seen during exploration; confirm the outputs stay out of git
- [ ] 5.2 Run `ruff check` and `ruff format` on the whole project, with the full test suite green afterwards

## Workflow follow-up

- Prerequisite before apply: the project is not yet a git repository. Initialise it, create and push `develop` to a remote, then branch from an up-to-date `develop`.
- Commit each task group separately using Conventional Commits; put the lint/format changes (5.2) in the last commit before the PR.
- Open the PR against `develop`.
- Archive the change once the PR is merged.
