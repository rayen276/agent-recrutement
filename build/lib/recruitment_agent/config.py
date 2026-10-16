"""Configuration chargée depuis l'environnement (.env supporté)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Fournisseurs supportés. Gemini et Groq ont un palier gratuit ; les noms de modèles
# évoluent : modifiez-les avec RH_MODEL si besoin.
PROVIDERS: dict[str, dict[str, str]] = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-3.8-flash",
        "key_env": "GEMINI_API_KEY",
        "key_url": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "key_url": "https://console.groq.com/keys",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_env": "OPENROUTER_API_KEY",
        "key_url": "https://openrouter.ai/keys",
    },
    "anthropic": {
        "base_url": "",
        "model": "claude-sonnet-5-5",
        "key_env": "ANTHROPIC_API_KEY",
        "key_url": "https://console.anthropic.com",
    },
}
DEFAULT_PROVIDER = "gemini"

# Budget de sortie (en jetons) par type de réponse structurée. Les modèles « raisonneurs »
# dépensent une partie de ce budget à réfléchir : mieux vaut large que tronqué.
STRUCTURED_BUDGETS: dict[str, int] = {
    "Analysis": 6000,
    "InterviewPrep": 10000,
    "MatchList": 3000,
    "Queries": 1500,
    "AnswerFeedback": 3500,
    "EmailDraft": 2500,
}
MAX_BUDGET = 16000


class ConfigError(RuntimeError):
    """Configuration manquante ou invalide."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    provider: str = DEFAULT_PROVIDER
    model: str = PROVIDERS[DEFAULT_PROVIDER]["model"]
    base_url: str = PROVIDERS[DEFAULT_PROVIDER]["base_url"]
    max_tokens_analysis: int = 6000  # large : certains modèles « réfléchissent » avant de répondre
    max_tokens_letter: int = 3000
    max_input_chars: int = 30_000  # garde-fou par document
    reasoning_effort: str = ""  # « low » réduit la réflexion des modèles gpt-oss (moins de jetons)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        provider = (os.getenv("RH_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
        if provider not in PROVIDERS:
            raise ConfigError(f"RH_PROVIDER inconnu : « {provider} ». Choix : {', '.join(PROVIDERS)}.")
        info = PROVIDERS[provider]

        key = (os.getenv(info["key_env"]) or os.getenv("RH_API_KEY") or "").strip().strip("\"'")
        if not key or key.endswith("..."):
            raise ConfigError(
                f"{info['key_env']} est vide ou contient encore le texte d'exemple. "
                f"Créez une clé sur {info['key_url']}, collez-la dans le fichier .env "
                f"({info['key_env']}=...) et enregistrez le fichier."
            )
        model = (os.getenv("RH_MODEL") or info["model"]).strip()
        effort = (os.getenv("RH_REASONING_EFFORT") or "").strip().lower()
        if not effort and provider == "groq" and "gpt-oss" in model:
            effort = "low"
        return cls(
            api_key=key,
            provider=provider,
            model=model,
            reasoning_effort=effort,
            base_url=(os.getenv("RH_BASE_URL") or info["base_url"]).strip().rstrip("/"),
        )
