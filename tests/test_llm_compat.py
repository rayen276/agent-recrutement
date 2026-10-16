import json

import pytest

from recruitment_agent.config import ConfigError, Settings
from recruitment_agent.llm import LLMError
from recruitment_agent.llm_compat import OpenAICompatLLM, extract_json
from recruitment_agent.models import Analysis

VALID = {
    "poste": "Dev", "score": 60, "resume": "ok",
    "points_forts": [{"titre": "a", "preuve": "b"}],
    "exigences": [{"exigence": "x", "statut": "couvert", "commentaire": "c"}],
    "mots_cles": {"presents": [], "manquants": []},
    "conseils_cv": ["z"], "angle_lettre": "angle",
}


def make(responses):
    llm = OpenAICompatLLM(Settings(api_key="k"))
    it = iter(responses)
    llm._chat = lambda messages, max_tokens, json_mode=False: next(it)
    return llm


def test_extract_json_handles_fences_and_noise():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Voici : {"a": 1} fin') == {"a": 1}


def test_structured_ok():
    a = make([json.dumps(VALID)]).structured("s", "u", Analysis)
    assert a.score == 60


def test_structured_retries_once_on_bad_json():
    a = make(["pas du json", json.dumps(VALID)]).structured("s", "u", Analysis)
    assert a.poste == "Dev"


def test_structured_gives_up():
    with pytest.raises(LLMError):
        make(["nope", "nope", "nope"]).structured("s", "u", Analysis)


def test_placeholder_key_is_rejected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RH_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-ant-...")
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_gemini_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RH_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFakeKeyForTest123")
    s = Settings.from_env()
    assert "generativelanguage.googleapis.com" in s.base_url


# -- quota (429) -------------------------------------------------------------
import io
import urllib.error

from recruitment_agent import llm_compat
from recruitment_agent.llm_compat import parse_wait_seconds


def _http_error(code, body, headers=None):
    from email.message import Message
    h = Message()
    for k, v in (headers or {}).items():
        h[k] = v
    return urllib.error.HTTPError("http://x", code, "err", h, io.BytesIO(body.encode()))


def test_parse_wait_seconds():
    assert parse_wait_seconds({"retry-after": "12"}, "") == 12.0
    assert parse_wait_seconds(None, "Please try again in 6.5s.") == 6.5
    assert parse_wait_seconds(None, "Please try again in 2m30.5s") == 150.5
    assert parse_wait_seconds(None, "Please retry in 27s") == 27.0
    assert parse_wait_seconds(None, "rien") is None


class _Resp:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.data


def test_429_waits_then_succeeds(monkeypatch):
    calls, waits, slept = {"n": 0}, [], []

    def fake_urlopen(req, timeout=0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(429, "Rate limit. Please try again in 3.2s")
        return _Resp(b'{"choices":[{"message":{"content":"ok"}}]}')

    monkeypatch.setattr(llm_compat.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(llm_compat.time, "sleep", slept.append)
    llm = OpenAICompatLLM(Settings(api_key="k"), on_wait=waits.append)
    assert llm._chat([{"role": "user", "content": "x"}], 10) == "ok"
    assert waits == [3.2] and slept == [4.2] and calls["n"] == 2


def test_429_long_wait_is_reported_not_slept(monkeypatch):
    slept = []
    monkeypatch.setattr(llm_compat.urllib.request, "urlopen",
                        lambda req, timeout=0: (_ for _ in ()).throw(_http_error(429, "Please try again in 1h2m3s")))
    monkeypatch.setattr(llm_compat.time, "sleep", slept.append)
    with pytest.raises(LLMError) as exc:
        OpenAICompatLLM(Settings(api_key="k"))._chat([], 10)
    assert "journalière" in str(exc.value) and "62 min" in str(exc.value) and slept == []


# -- réponses tronquées / JSON refusé par le fournisseur ----------------------
def make_recorder(steps):
    """steps : liste de (texte | LLMError, finish_reason). Enregistre (max_tokens, json_mode)."""
    llm = OpenAICompatLLM(Settings(api_key="k"))
    seen, it = [], iter(steps)

    def fake_chat(messages, max_tokens, json_mode=False):
        seen.append((max_tokens, json_mode))
        out, finish = next(it)
        llm.last_finish = finish
        if isinstance(out, Exception):
            raise out
        return out

    llm._chat = fake_chat
    return llm, seen


def test_truncated_json_is_retried_with_more_tokens():
    llm, seen = make_recorder([('{"poste": "Dev", "sc', "length"), (json.dumps(VALID), "stop")])
    assert llm.structured("s", "u", Analysis).poste == "Dev"
    assert seen[1][0] == seen[0][0] * 2


def test_provider_json_validate_failed_falls_back_without_json_mode():
    err = LLMError("json_validate_failed : tronqué")
    llm, seen = make_recorder([(err, None), (json.dumps(VALID), "stop")])
    assert llm.structured("s", "u", Analysis).score == 60
    assert seen[0][1] is True and seen[1][1] is False and seen[1][0] > seen[0][0]


def test_interview_gets_a_larger_budget_than_analysis():
    from recruitment_agent.config import STRUCTURED_BUDGETS
    assert STRUCTURED_BUDGETS["InterviewPrep"] > STRUCTURED_BUDGETS["Analysis"]


def test_reasoning_effort_is_dropped_if_provider_rejects_it(monkeypatch):
    payloads = []

    def fake_urlopen(req, timeout=0):
        body = json.loads(req.data.decode())
        payloads.append(body)
        if "reasoning_effort" in body:
            raise _http_error(400, '{"error":{"message":"unknown parameter: reasoning_effort"}}')
        return _Resp(b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}')

    monkeypatch.setattr(llm_compat.urllib.request, "urlopen", fake_urlopen)
    llm = OpenAICompatLLM(Settings(api_key="k", reasoning_effort="low"))
    assert llm._chat([{"role": "user", "content": "x"}], 10) == "ok"
    assert "reasoning_effort" in payloads[0] and "reasoning_effort" not in payloads[-1]
    assert llm._drop_reasoning is True


def test_groq_gpt_oss_defaults_to_low_reasoning(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RH_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RH_MODEL", "openai/gpt-oss-120b")
    monkeypatch.delenv("RH_REASONING_EFFORT", raising=False)
    assert Settings.from_env().reasoning_effort == "low"
