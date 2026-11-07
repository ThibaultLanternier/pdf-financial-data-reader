"""Check that the synthetic PDFs used by the other tests are read correctly by poppler."""

import pytest
from pdf_factory import make_corrupt_pdf, make_pdf, requires_poppler

from pdf_extractor import poppler
from pdf_extractor.poppler import PdfError

pytestmark = requires_poppler


def test_multi_page_pdf_is_readable(tmp_path):
    pdf = make_pdf(tmp_path / "a.pdf", [["SITUATION AU 31/01/2026"], ["TOTAL   12 345,67 €"], []])
    assert poppler.page_count(pdf) == 3
    text = poppler.layout_text(pdf)
    assert "SITUATION AU 31/01/2026" in text
    assert "12 345,67 €" in text
    assert text.count("\f") == 3


def test_textless_pdf_has_no_text(tmp_path):
    pdf = make_pdf(tmp_path / "scan.pdf", [[], []])
    assert poppler.page_count(pdf) == 2
    assert poppler.layout_text(pdf).replace("\f", "").strip() == ""


def test_corrupt_pdf_is_rejected(tmp_path):
    pdf = make_corrupt_pdf(tmp_path / "bad.pdf")
    with pytest.raises(PdfError):
        poppler.page_count(pdf)
