import json

import pytest
from pdf_factory import make_corrupt_pdf, make_pdf, requires_poppler

from pdf_extractor import cli, poppler


@pytest.fixture
def no_poppler(monkeypatch):
    monkeypatch.setattr(poppler.shutil, "which", lambda name: None)


class TestInputValidation:
    def test_missing_directory(self, tmp_path, capsys):
        missing = tmp_path / "nope"
        assert cli.main([str(missing), "-o", str(tmp_path / "out")]) == 2
        assert f"'{missing}' does not exist" in capsys.readouterr().err
        assert not (tmp_path / "out").exists()

    def test_file_instead_of_directory(self, tmp_path, capsys):
        file = tmp_path / "a.pdf"
        file.write_bytes(b"x")
        assert cli.main([str(file), "-o", str(tmp_path / "out")]) == 2
        assert "is not a directory" in capsys.readouterr().err

    def test_missing_tools_writes_nothing(self, tmp_path, capsys, no_poppler):
        make_pdf(tmp_path / "a.pdf", [["x"]])
        out = tmp_path / "out"
        assert cli.main([str(tmp_path), "-o", str(out)]) == 2
        assert "poppler-utils" in capsys.readouterr().err
        assert not out.exists()


class TestFindPdfs:
    def test_case_insensitive_sorted_non_recursive(self, tmp_path):
        for name in ["a.pdf", "B.PDF", "notes.txt", "c.Pdf"]:
            (tmp_path / name).write_bytes(b"x")
        (tmp_path / "old").mkdir()
        (tmp_path / "old" / "d.pdf").write_bytes(b"x")
        (tmp_path / "folder.pdf").mkdir()

        assert [p.name for p in cli.find_pdfs(tmp_path)] == ["B.PDF", "a.pdf", "c.Pdf"]


@requires_poppler
class TestRun:
    def test_empty_directory(self, tmp_path, capsys):
        out = tmp_path / "out"
        (tmp_path / "in").mkdir()
        assert cli.main([str(tmp_path / "in"), "-o", str(out)]) == 0
        assert "no PDF file found" in capsys.readouterr().out
        assert not out.exists()

    def test_all_succeed(self, tmp_path, capsys):
        src = tmp_path / "in"
        src.mkdir()
        make_pdf(src / "a.pdf", [["alpha"]])
        make_pdf(src / "b.pdf", [["beta"], ["page 2"]])
        out = tmp_path / "out"

        assert cli.main([str(src), "-o", str(out)]) == 0

        assert sorted(p.name for p in out.iterdir()) == ["a.pdf.json", "b.pdf.json"]
        assert json.loads((out / "b.pdf.json").read_text(encoding="utf-8"))["source"][
            "page_count"
        ] == 2
        stdout = capsys.readouterr().out.splitlines()
        assert stdout[0].startswith("OK   a.pdf -> ")
        assert stdout[1].startswith("OK   b.pdf -> ")
        assert stdout[-1] == "2 succeeded, 0 failed"

    def test_failures_are_isolated(self, tmp_path, capsys):
        src = tmp_path / "in"
        src.mkdir()
        make_pdf(src / "good.pdf", [["TOTAL 12 345,67 €"]])
        make_corrupt_pdf(src / "bad.pdf")
        make_pdf(src / "scan.pdf", [[], []])
        out = tmp_path / "out"

        assert cli.main([str(src), "-o", str(out)]) == 1

        assert [p.name for p in out.iterdir()] == ["good.pdf.json"]
        captured = capsys.readouterr()
        assert "FAIL bad.pdf: pdfinfo failed" in captured.err
        assert "FAIL scan.pdf: no text layer found" in captured.err
        assert captured.out.splitlines()[-1] == "1 succeeded, 2 failed"

    def test_default_output_directory(self, tmp_path, monkeypatch):
        src = tmp_path / "in"
        src.mkdir()
        make_pdf(src / "statement.pdf", [["x"]])
        monkeypatch.chdir(tmp_path)

        assert cli.main([str(src)]) == 0

        assert (tmp_path / "output" / "statement.pdf.json").is_file()


def test_help_runs(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "--output" in capsys.readouterr().out
