"""Client pour les API compatibles OpenAI (Gemini, Groq, OpenRouter…), sans dépendance externe."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from .config import MAX_BUDGET, STRUCTURED_BUDGETS, Settings
from .llm import LLMError

T = TypeVar("T", bound=BaseModel)

_RETRY_CODES = {500, 502, 503, 504}
MAX_AUTO_WAIT = 75.0      # attente automatique maximale (s) quand le quota par minute est atteint
LONG_WAIT = 120.0         # au-delà : probablement une limite journalière


def format_wait(seconds: float) -> str:
    if seconds < 120:
        return f"{int(seconds) + 1} s"
    if seconds < 7200:
        return f"{round(seconds / 60)} min"
    return f"{round(seconds / 3600)} h"


def parse_wait_seconds(headers, body: str) -> float | None:
    """Délai avant la prochaine tentative, d'après l'en-tête Retry-After ou le message du fournisseur."""
    try:
        ra = headers.get("retry-after") if headers else None
        if ra:
            return float(ra)
    except (TypeError, ValueError):
        pass
    m = re.search(r"(?:try again|retry) in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s", body or "", re.IGNORECASE)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3))
    return None


def extract_json(text: str) -> dict:
    """Extrait un objet JSON d'une réponse, même entourée de ```json ou de texte."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


class OpenAICompatLLM:
    def __init__(self, settings: Settings, retries: int = 2, timeout: int = 120, on_wait=None):
        self.settings = settings
        self.retries = retries
        self.timeout = timeout
        self.on_wait = on_wait  # rappel(secondes) appelé avant une attente liée au quota
        self.last_finish: str | None = None  # « length » = réponse tronquée
        self._drop_reasoning = False

    # -- HTTP --------------------------------------------------------------
    def _request(self, payload: dict) -> urllib.request.Request:
        return urllib.request.Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
                "User-Agent": "recruitment-agent/1.0",
            },
            method="POST",
        )

    def _explain(self, code: int, body: str, wait: float | None) -> LLMError:
        if code == 400 and "json_validate_failed" in (body or ""):
            return LLMError("json_validate_failed : le modèle n'a pas produit un JSON valide (réponse probablement tronquée).")
        body = (body or "")[:300]
        if code in (401, 403):
            return LLMError(f"Clé API refusée ({code}). Vérifiez la clé dans le fichier .env. {body}")
        if code == 404:
            return LLMError(f"Modèle introuvable ou retiré (404) : « {self.settings.model} ». Mettez à jour RH_MODEL dans le fichier .env avec le modèle indiqué ci-dessous, puis relancez. {body}")
        if code == 429:
            when = f" Réessayez dans environ {format_wait(wait)}." if wait else " Réessayez dans une minute."
            hint = ""
            if wait and wait > LONG_WAIT:
                hint = (" Cela ressemble à une limite journalière : changez de modèle (RH_MODEL) "
                        "ou de fournisseur (RH_PROVIDER).")
            return LLMError(f"Quota gratuit atteint (429).{when}{hint} Détail : {body}")
        return LLMError(f"Erreur du fournisseur ({code}) : {body}")

    def _post_with_retry(self, payload: dict, read):
        delay, attempts, quota_waits = 2.0, 0, 0
        while True:
            try:
                with urllib.request.urlopen(self._request(payload), timeout=self.timeout) as resp:
                    return read(resp)
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                if exc.code == 429:
                    wait = parse_wait_seconds(exc.headers, body)
                    if wait is not None and wait <= MAX_AUTO_WAIT and quota_waits < 3:
                        quota_waits += 1
                        if self.on_wait:
                            self.on_wait(wait)
                        time.sleep(wait + 1)
                        continue
                    raise self._explain(429, body, wait) from exc
                if exc.code in _RETRY_CODES and attempts < self.retries:
                    attempts += 1
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise self._explain(exc.code, body, None) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempts < self.retries:
                    attempts += 1
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise LLMError(f"Connexion impossible au fournisseur : {exc}") from exc

    # -- appel non-streaming ----------------------------------------------
    def _with_reasoning(self, payload: dict) -> dict:
        if self.settings.reasoning_effort and not self._drop_reasoning:
            payload["reasoning_effort"] = self.settings.reasoning_effort
        return payload

    def _post(self, payload: dict, read):
        """Envoie la requête ; si le fournisseur refuse `reasoning_effort`, réessaie sans."""
        try:
            return self._post_with_retry(payload, read)
        except LLMError as exc:
            if "reasoning_effort" in payload and "reasoning" in str(exc).lower():
                self._drop_reasoning = True
                payload = {k: v for k, v in payload.items() if k != "reasoning_effort"}
                return self._post_with_retry(payload, read)
            raise

    def _chat(self, messages: list[dict], max_tokens: int, json_mode: bool = False) -> str:
        payload: dict = {
            "model": self.settings.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        self._with_reasoning(payload)

        def read(resp):
            data = json.loads(resp.read().decode("utf-8"))
            try:
                choice = data["choices"][0]
                self.last_finish = choice.get("finish_reason")
                return choice["message"]["content"] or ""
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMError(f"Réponse inattendue du fournisseur : {str(data)[:200]}") from exc

        return self._post(payload, read)

    # -- sortie structurée -------------------------------------------------
    def structured(self, system: str, user: str, schema: type[T], tool_name: str = "") -> T:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_system = (
            f"{system}\n\nRéponds UNIQUEMENT par un objet JSON valide respectant ce JSON Schema "
            f"(aucun texte autour, pas de markdown, toutes les clés requises présentes) :\n{schema_json}"
        )
        base = [{"role": "system", "content": full_system}, {"role": "user", "content": user}]
        messages = list(base)
        tokens = STRUCTURED_BUDGETS.get(schema.__name__, self.settings.max_tokens_analysis)
        json_mode = True

        last_error = ""
        for _ in range(3):
            self.last_finish = None
            try:
                raw = self._chat(messages, tokens, json_mode=json_mode)
            except LLMError as exc:
                if "json_validate_failed" in str(exc):  # JSON invalide ou tronqué côté fournisseur
                    last_error = str(exc)
                    tokens, json_mode = min(tokens * 2, MAX_BUDGET), False
                    continue
                raise
            try:
                return schema.model_validate(extract_json(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = str(exc)[:400]
                if self.last_finish == "length":  # tronqué : on redemande avec plus de place
                    tokens = min(tokens * 2, MAX_BUDGET)
                    messages = list(base)
                    continue
                messages = base + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": f"Ce JSON est invalide ({last_error}). Renvoie uniquement le JSON corrigé et complet.",
                    },
                ]
        raise LLMError(f"Le modèle n'a pas produit une réponse valide après plusieurs essais : {last_error}")

    # -- texte en streaming ------------------------------------------------
    def text(self, system: str, user: str, on_delta: Callable[[str], None] | None = None) -> str:
        payload = {
            "model": self.settings.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": self.settings.max_tokens_letter,
            "temperature": 0.7,
            "stream": True,
        }
        self._with_reasoning(payload)
        chunks: list[str] = []

        def read(resp):
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    choices = json.loads(data).get("choices") or []
                except json.JSONDecodeError:
                    continue
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content") or ""
                if delta:
                    chunks.append(delta)
                    if on_delta:
                        on_delta(delta)
            return "".join(chunks)

        text = self._post(payload, read).strip()
        if not text:
            raise LLMError("Le modèle a renvoyé une lettre vide. Réessayez.")
        return text
