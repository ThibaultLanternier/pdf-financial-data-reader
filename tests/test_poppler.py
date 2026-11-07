import subprocess
from pathlib import Path

import pytest

from pdf_extractor import poppler
from pdf_extractor.poppler import PdfError, ToolError


def _completed(stdout=b"", stderr=b"", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def tools_on_path(monkeypatch):
    monkeypatch.setattr(poppler.shutil, "which", lambda name: f"/usr/bin/{name}")


@pytest.fixture
def fake_run(monkeypatch):
    """Replace subprocess.run with a stub returning (or raising) a configurable result."""
    calls = []

    def install(result):
        def run(args, **kwargs):
            calls.append((args, kwargs))
            if isinstance(result, BaseException):
                raise result
            return result

        monkeypatch.setattr(poppler.subprocess, "run", run)
        return calls

    return install


class TestCheckTools:
    def test_version_parsed_from_stderr(self, tools_on_path, fake_run):
        fake_run(_completed(stdout="", stderr="pdftotext version 24.02.0\nCopyright..."))
        assert poppler.check_tools() == "24.02.0"

    def test_version_parsed_from_stdout(self, tools_on_path, fake_run):
        fake_run(_completed(stdout="pdftotext version 23.08.0\n", stderr=""))
        assert poppler.check_tools() == "23.08.0"

    @pytest.mark.parametrize("missing", ["pdftotext", "pdfinfo"])
    def test_missing_binary(self, monkeypatch, missing):
        monkeypatch.setattr(
            poppler.shutil, "which", lambda name: None if name == missing else f"/usr/bin/{name}"
        )
        with pytest.raises(ToolError, match=f"'{missing}' not found.*poppler-utils"):
            poppler.check_tools()

    def test_unparsable_version(self, tools_on_path, fake_run):
        fake_run(_completed(stdout="", stderr="something unexpected"))
        with pytest.raises(ToolError, match="version"):
            poppler.check_tools()


class TestPageCount:
    def test_success(self, fake_run):
        calls = fake_run(_completed(stdout=b"Title:          x\nPages:          22\nEncrypted: no\n"))
        assert poppler.page_count(Path("a.pdf")) == 22
        args, kwargs = calls[0]
        assert args == ["pdfinfo", "a.pdf"]
        assert kwargs["timeout"] == poppler.TIMEOUT_SECONDS

    def test_non_zero_exit(self, fake_run):
        fake_run(_completed(stderr=b"Syntax Error: x\nSyntax Error: Couldn't read xref table\n",
                            returncode=1))
        with pytest.raises(PdfError, match="exit 1.*Couldn't read xref table"):
            poppler.page_count(Path("bad.pdf"))

    def test_timeout(self, fake_run):
        fake_run(subprocess.TimeoutExpired(cmd="pdfinfo", timeout=60))
        with pytest.raises(PdfError, match="timed out"):
            poppler.page_count(Path("slow.pdf"))

    def test_missing_pages_line(self, fake_run):
        fake_run(_completed(stdout=b"Title: x\n"))
        with pytest.raises(PdfError, match="page count"):
            poppler.page_count(Path("a.pdf"))


class TestLayoutText:
    def test_success(self, fake_run):
        calls = fake_run(_completed(stdout="TOTAL      12 345,67 €\n\f".encode()))
        assert poppler.layout_text(Path("a.pdf")) == "TOTAL      12 345,67 €\n\f"
        args, kwargs = calls[0]
        assert args == ["pdftotext", "-layout", "-enc", "UTF-8", "a.pdf", "-"]
        assert kwargs["timeout"] == poppler.TIMEOUT_SECONDS

    def test_non_zero_exit(self, fake_run):
        fake_run(_completed(stderr=b"I/O Error: Couldn't open file\n", returncode=1))
        with pytest.raises(PdfError, match="pdftotext failed.*Couldn't open file"):
            poppler.layout_text(Path("a.pdf"))

    def test_timeout(self, fake_run):
        fake_run(subprocess.TimeoutExpired(cmd="pdftotext", timeout=60))
        with pytest.raises(PdfError, match="timed out after 60 s"):
            poppler.layout_text(Path("a.pdf"))
