import pytest

from recruitment_agent import cli, jobs, mailer
from recruitment_agent.agent import InputError, RecruitmentAgent
from recruitment_agent.exporters import interview_docx_bytes, interview_markdown
from recruitment_agent.models import InterviewQuestion, JobOffer

from conftest import LONG_CV, LONG_OFFRE


# -- agent -----------------------------------------------------------------
def test_suggest_queries_cleans_blanks(fake_llm):
    assert RecruitmentAgent(fake_llm).suggest_queries(LONG_CV) == ["digital marketing", "growth marketer"]


def test_rank_offers_sorts_and_handles_unknown_and_missing(fake_llm):
    offers = [JobOffer(id=str(i), titre=f"Poste {i}") for i in (1, 2, 3)]
    ranked = RecruitmentAgent(fake_llm).rank_offers(LONG_CV, offers)
    assert [o.id for o, _ in ranked] == ["2", "1", "3"]          # id « 99 » ignoré, « 3 » ajouté
    assert ranked[-1][1].raison == "Non évaluée."


def test_interview_and_feedback(fake_llm):
    agent = RecruitmentAgent(fake_llm)
    prep = agent.prepare_interview(LONG_CV, LONG_OFFRE)
    assert prep.questions[0].question == "Parlez de GA4"
    fb = agent.evaluate_answer(LONG_CV, LONG_OFFRE, prep.questions[0], "Ma réponse détaillée sur GA4 et ses usages.")
    assert fb.note == 7
    with pytest.raises(InputError):
        agent.evaluate_answer(LONG_CV, LONG_OFFRE, prep.questions[0], "court")


def test_interview_exports(fake_llm):
    prep = RecruitmentAgent(fake_llm).prepare_interview(LONG_CV, LONG_OFFRE)
    assert "Parlez de GA4" in interview_markdown(prep)
    assert interview_docx_bytes(prep)[:2] == b"PK"


# -- offres ----------------------------------------------------------------
def test_strip_html():
    assert jobs.strip_html("<p>Bonjour&nbsp;<b>monde</b></p><ul><li>A</li><li>B</li></ul>").replace("\xa0", " ").split() == ["Bonjour", "monde", "A", "B"]


def test_search_jobs_dedupes_and_tolerates_errors(monkeypatch):
    def fake_get(url, timeout=20):
        if "remotive" in url:
            return {"jobs": [
                {"title": "Growth Marketer", "company_name": "Acme", "url": "https://x/1", "description": "<p>Desc</p>"},
                {"title": "Growth Marketer", "company_name": "Acme", "url": "https://x/1", "description": "dup"},
            ]}
        raise jobs.JobSearchError("arbeitnow : hors ligne")

    monkeypatch.setattr(jobs, "get_json", fake_get)
    offers, errors = jobs.search_jobs(["growth marketer", "marketing"])
    assert [o.id for o in offers] == ["1"] and offers[0].description == "Desc"
    assert errors == ["arbeitnow : hors ligne"]


def test_arbeitnow_filters_locally(monkeypatch):
    data = {"data": [
        {"title": "Python Developer", "company_name": "A", "tags": [], "url": "u1", "created_at": 1700000000},
        {"title": "Cuisinier", "company_name": "B", "tags": [], "url": "u2"},
    ]}
    monkeypatch.setattr(jobs, "get_json", lambda url, timeout=20: data)
    res = jobs.search_arbeitnow("python developer")
    assert [o.entreprise for o in res] == ["A"] and res[0].date == "2023-11-14"


def test_manual_links_are_encoded():
    assert "data+analyst" in jobs.manual_search_links("data analyst", "Tunis")["LinkedIn"]


# -- e-mail ----------------------------------------------------------------
def test_validate_address():
    assert mailer.validate_address(" rh@exemple.com ") == "rh@exemple.com"
    for bad in ("", "pas-un-mail", "a@b", "a@b.com\nBcc: x@y.com"):
        with pytest.raises(mailer.MailError):
            mailer.validate_address(bad)


def test_build_message_blocks_header_injection_and_attaches():
    msg = mailer.build_message("rh@exemple.com", "Candidature\nBcc: evil@x.com", "Corps", [("cv.pdf", b"%PDF-1.4")])
    assert "\n" not in msg["Subject"] and msg["Bcc"] is None
    assert [p.get_filename() for p in msg.iter_attachments()] == ["cv.pdf"]
    assert b"rh@exemple.com" in mailer.to_eml(msg)


def test_smtp_settings_requires_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    from recruitment_agent.config import ConfigError
    with pytest.raises(ConfigError):
        mailer.SmtpSettings.from_env()


def test_draft_email_uses_agent(fake_llm):
    d = RecruitmentAgent(fake_llm).draft_email(LONG_CV, entreprise="Atlas", poste="Growth")
    assert d.corps.startswith("Bonjour")


# -- CLI -------------------------------------------------------------------
def test_cli_legacy_arguments_map_to_candidater():
    assert cli._normalize_argv(["--cv", "a", "--offre", "b"])[0] == "candidater"
    assert cli._normalize_argv(["offres", "--cv", "a"])[0] == "offres"
    args = cli.build_parser().parse_args(cli._normalize_argv(["--cv", "a", "--offre", "b"]))
    assert args.cmd == "candidater"


def test_cli_email_does_not_send_by_default():
    args = cli.build_parser().parse_args(["email", "--cv", "a", "--a", "rh@exemple.com"])
    assert args.envoyer is False and args.oui is False


def test_job_offer_as_text():
    assert JobOffer(id="1", titre="Dev", entreprise="X", description="Desc").as_text().startswith("Dev — X")
