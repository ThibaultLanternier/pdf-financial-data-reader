import hashlib
import json
import re
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pdf_factory import make_pdf, requires_poppler

from pdf_extractor.poppler import PdfError
from pdf_extractor.snapshot import build_snapshot, split_pages, write_snapshot

FIXED_NOW = datetime(2026, 11, 7, 9, 42, 13, 987654, tzinfo=UTC)


class TestSplitPages:
    def test_trailing_form_feed_is_stripped(self):
        assert split_pages("page 1\n\fpage 2\n\f", 2) == ["page 1\n", "page 2\n"]

    def test_without_trailing_form_feed(self):
        assert split_pages("page 1\n\fpage 2\n", 2) == ["page 1\n", "page 2\n"]

    def test_empty_middle_page_is_kept(self):
        assert split_pages("a\n\f\fc\n\f", 3) == ["a\n", "", "c\n"]

    def test_text_is_not_modified(self):
        page = "   TOTAL      12 345,67 €   \r\n\n"
        assert split_pages(page + "\f", 1) == [page]

    def test_page_count_mismatch(self):
        with pytest.raises(PdfError, match="returned 2 pages but pdfinfo reports 3"):
            split_pages("a\fb\f", 3)

    def test_whitespace_only_text_means_no_text_layer(self):
        with pytest.raises(PdfError, match="no text layer"):
            split_pages("\n  \f\n\f", 2)


@requires_poppler
class TestBuildSnapshot:
    def test_document_fields(self, tmp_path):
        pdf = make_pdf(tmp_path / "statement.pdf", [["SITUATION AU 31/01/2026"], ["TOTAL 1,00 €"]])
        snapshot = build_snapshot(pdf, "24.02.0", now=FIXED_NOW)

        assert list(snapshot) == ["schema_version", "source", "extraction", "pages"]
        assert snapshot["schema_version"] == 1
        assert snapshot["source"] == {
            "file_name": "statement.pdf",
            "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "page_count": 2,
        }
        assert snapshot["extraction"] == {
            "extracted_at": "2026-11-07T09:42:13Z",
            "tool": "pdftotext",
            "tool_version": "24.02.0",
            "mode": "layout",
        }
        assert len(snapshot["pages"]) == 2
        assert "SITUATION AU 31/01/2026" in snapshot["pages"][0]
        assert "TOTAL 1,00 €" in snapshot["pages"][1]
        assert "SITUATION" not in snapshot["pages"][1]

    def test_timestamp_is_utc_with_z_suffix(self, tmp_path):
        pdf = make_pdf(tmp_path / "a.pdf", [["x"]])
        paris = timezone(timedelta(hours=1))
        stamped = build_snapshot(pdf, "24.02.0", now=datetime(2026, 11, 7, 10, 0, 0, tzinfo=paris))
        assert stamped["extraction"]["extracted_at"] == "2026-11-07T09:00:00Z"

        default = build_snapshot(pdf, "24.02.0")["extraction"]["extracted_at"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", default)

    def test_file_name_has_no_directory(self, tmp_path):
        nested = tmp_path / "deep" / "dir"
        nested.mkdir(parents=True)
        pdf = make_pdf(nested / "a.pdf", [["x"]])
        assert build_snapshot(pdf, "24.02.0")["source"]["file_name"] == "a.pdf"

    def test_textless_pdf_is_rejected(self, tmp_path):
        pdf = make_pdf(tmp_path / "scan.pdf", [[], []])
        with pytest.raises(PdfError, match="no text layer"):
            build_snapshot(pdf, "24.02.0")


@requires_poppler
class TestWriteSnapshot:
    def test_writes_utf8_json_named_after_pdf(self, tmp_path):
        pdf = make_pdf(tmp_path / "statement.pdf", [["TOTAL 12 345,67 €"]])
        out = tmp_path / "out"
        out.mkdir()

        target = write_snapshot(build_snapshot(pdf, "24.02.0", now=FIXED_NOW), out)

        assert target == out / "statement.pdf.json"
        raw = target.read_text(encoding="utf-8")
        assert "€" in raw and "\\u20ac" not in raw
        assert raw.endswith("}\n")
        assert raw.startswith('{\n  "schema_version": 1,')
        assert json.loads(raw)["source"]["file_name"] == "statement.pdf"
        assert [p.name for p in out.iterdir()] == ["statement.pdf.json"]

    def test_rewrite_overwrites(self, tmp_path):
        pdf = make_pdf(tmp_path / "a.pdf", [["first"]])
        out = tmp_path / "out"
        out.mkdir()
        (out / "a.pdf.json").write_text("stale", encoding="utf-8")

        write_snapshot(build_snapshot(pdf, "24.02.0"), out)

        assert json.loads((out / "a.pdf.json").read_text(encoding="utf-8"))["schema_version"] == 1

    def test_two_runs_differ_only_in_timestamp(self, tmp_path):
        pdf = make_pdf(tmp_path / "a.pdf", [["line one", "line two"], ["page two"]])
        first_dir, second_dir = tmp_path / "1", tmp_path / "2"
        first_dir.mkdir()
        second_dir.mkdir()

        first = write_snapshot(build_snapshot(pdf, "24.02.0", now=FIXED_NOW), first_dir)
        later = FIXED_NOW + timedelta(hours=1)
        second = write_snapshot(build_snapshot(pdf, "24.02.0", now=later), second_dir)

        a = json.loads(first.read_text(encoding="utf-8"))
        b = json.loads(second.read_text(encoding="utf-8"))
        assert a["extraction"].pop("extracted_at") != b["extraction"].pop("extracted_at")
        assert a == b
