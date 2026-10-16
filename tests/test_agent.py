import pytest

from recruitment_agent.agent import InputError, RecruitmentAgent
from recruitment_agent.models import LetterOptions

from conftest import LONG_CV, LONG_OFFRE


def test_run_pipeline(fake_llm):
    steps, deltas = [], []
    agent = RecruitmentAgent(fake_llm)
    result = agent.run(LONG_CV, LONG_OFFRE, LetterOptions(), on_step=steps.append, on_delta=deltas.append)
    assert steps == ["analyse", "lettre", "termine"]
    assert result.analysis.score == 72
    assert "Sarra Ben Ali" in result.letter
    assert deltas


def test_rejects_short_inputs(fake_llm):
    agent = RecruitmentAgent(fake_llm)
    with pytest.raises(InputError):
        agent.analyze("trop court", LONG_OFFRE)
    with pytest.raises(InputError):
        agent.analyze(LONG_CV, "")


def test_truncates_long_inputs(fake_llm):
    agent = RecruitmentAgent(fake_llm, max_input_chars=500)
    agent.analyze("x" * 5000, LONG_OFFRE)
    user_prompt = fake_llm.calls[0][1]
    assert "x" * 501 not in user_prompt


def test_letter_revision_includes_feedback(fake_llm):
    agent = RecruitmentAgent(fake_llm)
    analysis = agent.analyze(LONG_CV, LONG_OFFRE)
    agent.write_letter(LONG_CV, LONG_OFFRE, analysis, previous="Ancienne lettre", feedback="plus court")
    prompt = fake_llm.calls[-1][1]
    assert "Ancienne lettre" in prompt and "plus court" in prompt
