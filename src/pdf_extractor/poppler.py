"""Thin wrapper around the poppler-utils binaries ``pdftotext`` and ``pdfinfo``."""

import re
import shutil
import subprocess
from pathlib import Path

PDFTOTEXT = "pdftotext"
PDFINFO = "pdfinfo"
TIMEOUT_SECONDS = 60

_VERSION_RE = re.compile(r"pdftotext version (\S+)")
_PAGES_RE = re.compile(r"^Pages:\s+(\d+)\s*$", re.MULTILINE)


class ToolError(Exception):
    """The extraction tools are missing or unusable; nothing can be processed."""


class PdfError(Exception):
    """A single PDF could not be processed."""


def check_tools() -> str:
    """Ensure both binaries are on PATH and return the poppler version."""
    for name in (PDFTOTEXT, PDFINFO):
        if shutil.which(name) is None:
            raise ToolError(f"'{name}' not found on PATH; install poppler-utils")
    try:
        result = subprocess.run(
            [PDFTOTEXT, "-v"], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolError(f"could not run '{PDFTOTEXT} -v': {exc}") from exc
    # poppler prints its version on stderr; search both streams to be safe.
    match = _VERSION_RE.search(result.stdout + result.stderr)
    if match is None:
        raise ToolError(f"could not determine the {PDFTOTEXT} version")
    return match.group(1)


def page_count(path: Path) -> int:
    """Return the number of pages reported by ``pdfinfo``."""
    output = _run([PDFINFO, str(path)]).decode("utf-8", errors="replace")
    match = _PAGES_RE.search(output)
    if match is None:
        raise PdfError(f"{PDFINFO} did not report a page count")
    return int(match.group(1))


def layout_text(path: Path) -> str:
    """Return the ``pdftotext -layout`` output for the whole document."""
    output = _run([PDFTOTEXT, "-layout", "-enc", "UTF-8", str(path), "-"])
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PdfError(f"{PDFTOTEXT} returned invalid UTF-8: {exc}") from exc


def _run(args: list[str]) -> bytes:
    try:
        result = subprocess.run(args, capture_output=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise PdfError(f"{args[0]} timed out after {TIMEOUT_SECONDS} s") from exc
    except OSError as exc:
        raise PdfError(f"could not run {args[0]}: {exc}") from exc
    if result.returncode != 0:
        raise PdfError(f"{args[0]} failed (exit {result.returncode}): {_last_line(result.stderr)}")
    return result.stdout


def _last_line(stderr: bytes) -> str:
    lines = [line for line in stderr.decode("utf-8", errors="replace").splitlines() if line.strip()]
    return lines[-1].strip() if lines else "no error message"
