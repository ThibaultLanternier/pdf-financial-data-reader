"""Build and write the JSON text snapshot of one PDF."""

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pdf_extractor import poppler
from pdf_extractor.poppler import PdfError

SCHEMA_VERSION = 1
MODE = "layout"
_CHUNK_SIZE = 1024 * 1024


def split_pages(text: str, expected_pages: int) -> list[str]:
    """Split pdftotext output into pages and check it against the expected page count."""
    # pdftotext ends every page, including the last one, with a form feed.
    if text.endswith("\f"):
        text = text[:-1]
    pages = text.split("\f")
    if len(pages) != expected_pages:
        raise PdfError(
            f"{poppler.PDFTOTEXT} returned {len(pages)} pages "
            f"but {poppler.PDFINFO} reports {expected_pages}"
        )
    if all(not page.strip() for page in pages):
        raise PdfError("no text layer found (scanned or image-only PDF?)")
    return pages


def build_snapshot(
    path: Path, tool_version: str, now: datetime | None = None
) -> dict[str, Any]:
    """Extract the layout text of ``path`` and return the snapshot document."""
    page_count = poppler.page_count(path)
    pages = split_pages(poppler.layout_text(path), page_count)
    extracted_at = (now or datetime.now(UTC)).astimezone(UTC)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "file_name": path.name,
            "sha256": _sha256(path),
            "page_count": page_count,
        },
        "extraction": {
            "extracted_at": extracted_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool": poppler.PDFTOTEXT,
            "tool_version": tool_version,
            "mode": MODE,
        },
        "pages": pages,
    }


def output_path(output_dir: Path, file_name: str) -> Path:
    return output_dir / f"{file_name}.json"


def write_snapshot(snapshot: dict[str, Any], output_dir: Path) -> Path:
    """Write the snapshot atomically to ``<output_dir>/<file name>.json``."""
    target = output_path(output_dir, snapshot["source"]["file_name"])
    content = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=output_dir, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
