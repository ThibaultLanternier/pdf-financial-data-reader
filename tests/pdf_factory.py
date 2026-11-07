"""Write minimal, valid PDF files for tests using only the standard library.

Each page is a list of text lines drawn in Helvetica; an empty list gives a page
with no text at all, which is how a scanned (image-only) page looks to pdftotext.
"""

import shutil
from pathlib import Path

import pytest

requires_poppler = pytest.mark.skipif(
    shutil.which("pdftotext") is None or shutil.which("pdfinfo") is None,
    reason="poppler-utils (pdftotext, pdfinfo) is not installed",
)


def make_pdf(path: Path, pages: list[list[str]]) -> Path:
    font_id = 3
    page_ids = [4 + 2 * i for i in range(len(pages))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (b" ".join(b"%d 0 R" % pid for pid in page_ids), len(pages)),
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
    }
    for page_id, lines in zip(page_ids, pages, strict=True):
        content = _content_stream(lines)
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (font_id, page_id + 1)
        )
        objects[page_id + 1] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content)

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (obj_id, objects[obj_id])
    xref_offset = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for obj_id in sorted(objects):
        out += b"%010d 00000 n \n" % offsets[obj_id]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_offset,
    )
    path.write_bytes(bytes(out))
    return path


def make_corrupt_pdf(path: Path) -> Path:
    path.write_bytes(b"this is not a pdf")
    return path


def _content_stream(lines: list[str]) -> bytes:
    if not lines:
        return b""
    parts = [b"BT /F1 12 Tf 14 TL 72 770 Td"]
    for i, line in enumerate(lines):
        parts.append((b"" if i == 0 else b"T* ") + b"(" + _escape(line) + b") Tj")
    parts.append(b"ET")
    return b"\n".join(parts)


def _escape(text: str) -> bytes:
    raw = text.encode("cp1252")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
