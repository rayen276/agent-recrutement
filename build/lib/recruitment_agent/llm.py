"""Clients LLM : Anthropic (SDK) et API compatible OpenAI (Gemini, Groq, OpenRouter…)."""

from __future__ import annotations

import time
from typing import Callable, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .config import STRUCTURED_BUDGETS, Settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Erreur lors de l'appel au modèle."""


class LLMClient(Protocol):
    """Interface minimale : permet de substituer un faux client dans les tests."""

    def structured(self, system: str, user: str, schema: type[T], tool_name: str) -> T: ...

    def text(self, system: str, user: str, on_delta: Callable[[str], None] | None = None) -> str: ...


def build_llm(settings: Settings) -> LLMClient:
    """Crée le client correspondant au fournisseur configuré."""
    if settings.provider == "anthropic":
        return AnthropicLLM(settings)
    from .llm_compat import OpenAICompatLLM

    return OpenAICompatLLM(settings)


class AnthropicLLM:
    """Claude via le SDK officiel (installation : pip install anthropic)."""

    def __init__(self, settings: Settings, client=None, retries: int = 2):
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError("Le paquet « anthropic » est requis : pip install anthropic") from exc
        self._a = anthropic
        self.settings = settings
        self.client = client or anthropic.Anthropic(api_key=settings.api_key)
        self.retries = retries

    def _with_retry(self, fn):
        a, delay = self._a, 1.5
        for attempt in range(self.retries + 1):
            try:
                return fn()
            except (a.RateLimitError, a.APIConnectionError, a.InternalServerError) as exc:
                if attempt == self.retries:
                    raise LLMError(f"Service momentanément indisponible : {exc}") from exc
                time.sleep(delay)
                delay *= 2
            except a.AuthenticationError as exc:
                raise LLMError("Clé API invalide ou refusée.") from exc
            except a.APIStatusError as exc:
                raise LLMError(f"Erreur API ({exc.status_code}) : {exc.message}") from exc

    def structured(self, system: str, user: str, schema: type[T], tool_name: str = "submit_analysis") -> T:
        tool = {
            "name": tool_name,
            "description": "Soumet l'analyse structurée finale.",
            "input_schema": schema.model_json_schema(),
        }

        def call():
            return self.client.messages.create(
                model=self.settings.model,
                max_tokens=STRUCTURED_BUDGETS.get(schema.__name__, self.settings.max_tokens_analysis),
                system=system,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": user}],
            )

        response = self._with_retry(call)
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                try:
                    return schema.model_validate(block.input)
                except ValidationError as exc:
                    raise LLMError(f"Réponse du modèle invalide : {exc}") from exc
        raise LLMError("Le modèle n'a pas renvoyé de résultat structuré.")

    def text(self, system: str, user: str, on_delta: Callable[[str], None] | None = None) -> str:
        def call():
            chunks: list[str] = []
            with self.client.messages.stream(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens_letter,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                for delta in stream.text_stream:
                    chunks.append(delta)
                    if on_delta:
                        on_delta(delta)
            return "".join(chunks)

        return self._with_retry(call).strip()
