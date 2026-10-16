import io

from docx import Document

from recruitment_agent.exporters import letter_docx_bytes, report_markdown, save_all
from recruitment_agent.models import Result

from conftest import FakeLLM


def _analysis():
    return FakeLLM().structured("", "", None, "")


def test_report_markdown_contains_score():
    md = report_markdown(_analysis())
    assert "72/100" in md and "TikTok Ads" in md


def test_letter_docx_is_valid():
    data = letter_docx_bytes("Bonjour.\n\nMerci.")
    doc = Document(io.BytesIO(data))
    assert [p.text for p in doc.paragraphs] == ["Bonjour.", "Merci."]


def test_save_all_writes_files(tmp_path):
    paths = save_all(Result(analysis=_analysis(), letter="Lettre"), tmp_path / "out")
    assert set(paths) == {"analyse.json", "rapport.md", "rapport.docx", "lettre.md", "lettre.docx"}
    assert all(p.exists() and p.stat().st_size > 0 for p in paths.values())
