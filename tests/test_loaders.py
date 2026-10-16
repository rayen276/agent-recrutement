import io

import pytest
from docx import Document

from recruitment_agent.loaders import LoaderError, clean_text, load_bytes, load_file


def test_txt_utf8_and_latin1():
    assert load_bytes("a.txt", "Éducation".encode("utf-8")) == "Éducation"
    assert load_bytes("a.txt", "Éducation".encode("cp1252")) == "Éducation"


def test_docx_roundtrip():
    doc = Document()
    doc.add_paragraph("Ingénieure logiciel")
    buf = io.BytesIO()
    doc.save(buf)
    assert "Ingénieure logiciel" in load_bytes("cv.docx", buf.getvalue())


def test_unsupported_format():
    with pytest.raises(LoaderError):
        load_bytes("cv.exe", b"abc")


def test_missing_file(tmp_path):
    with pytest.raises(LoaderError):
        load_file(tmp_path / "nope.txt")


def test_clean_text_collapses_blank_lines():
    assert clean_text("a\r\n\r\n\r\n\r\nb  \n") == "a\n\nb"
