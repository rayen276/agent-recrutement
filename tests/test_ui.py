from pathlib import Path

import pytest

from recruitment_agent import ui
from recruitment_agent.models import Analysis

from conftest import FakeLLM


def _analysis(**over) -> Analysis:
    a = FakeLLM().structured("", "", Analysis, "").model_dump()
    a.update(over)
    return Analysis.model_validate(a)


def test_esc_blocks_html_injection():
    assert "<script>" not in ui.esc("<script>alert(1)</script>")
    assert "&lt;b&gt;" in ui.esc("<b>")


def test_metrics_from_requirements_and_keywords():
    a = _analysis(
        exigences=[
            {"exigence": "A", "statut": "couvert", "commentaire": ""},
            {"exigence": "B", "statut": "partiel", "commentaire": ""},
            {"exigence": "C", "statut": "absent", "commentaire": ""},
            {"exigence": "D", "statut": "couvert", "commentaire": ""},
        ],
        mots_cles={"presents": ["x", "y", "z"], "manquants": ["w"]},
    )
    m = ui.compute_metrics(a)
    assert m["req_pct"] == 63          # (2 + 0,5) / 4
    assert m["kw_pct"] == 75
    assert m["to_fix_pct"] == 50
    assert [r.exigence for r in m["absent"]] == ["C"]


def test_metrics_handle_empty_lists():
    a = _analysis(exigences=[], mots_cles={"presents": [], "manquants": []})
    m = ui.compute_metrics(a)
    assert m["kw_pct"] is None and m["req_pct"] == 0
    assert "—" in ui.kpi_row(a)


def test_kpi_row_shows_score_and_escapes_model_text():
    a = _analysis(score=88, mots_cles={"presents": [], "manquants": ["<img src=x onerror=alert(1)>"]})
    out = ui.kpi_row(a)
    assert "88" in out and "<img" not in out and "&lt;img" in out
    assert "conic-gradient(#10b981 88%" in out


@pytest.mark.parametrize("score,color", [(80, "#10b981"), (60, "#f59e0b"), (20, "#ef4444")])
def test_verdict_colors(score, color):
    assert ui._verdict(score)[0] == color


def test_letter_doc_highlights_keywords_without_breaking_html():
    letter = "Objet : Candidature <b>\n\nJe maîtrise Spring Boot et docker.\n\nSarra Ben Ali"
    out = ui.letter_doc(letter, ["Spring Boot", "Docker", "x"])
    assert '<p class="obj">' in out and "&lt;b&gt;" in out       # texte échappé
    assert out.count("<mark") == 2                                # « x » trop court, ignoré
    assert '<p class="sig">' in out


def test_letter_doc_without_keywords():
    assert "<mark" not in ui.letter_doc("Bonjour.\n\nMerci.")


def test_skills_matrix_groups_items():
    out = ui.skills_matrix(_analysis())
    assert "Acquis" in out and "Non mentionné" in out and "TikTok Ads" in out


def test_markup_has_no_blank_lines_or_indented_blocks():
    """Markdown transformerait une ligne indentée de 4 espaces en bloc de code."""
    for html in (ui.brand(), ui.page_title(), ui.kpi_row(_analysis()), ui.skills_matrix(_analysis())):
        assert "\n    " not in html and "\n\n" not in html


def test_streamlit_app_renders_without_exception(monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("RH_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test")
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert list(at.radio[0].options) == ["Analyse CV & offre", "Offres", "Entretien", "E-mail"]
