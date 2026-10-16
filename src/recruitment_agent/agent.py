"""Orchestration : analyse CV/offre puis rédaction de la lettre."""

from __future__ import annotations

from typing import Callable

from . import prompts
from .llm import LLMClient
from .models import (
    Analysis,
    AnswerFeedback,
    EmailDraft,
    InterviewPrep,
    InterviewQuestion,
    JobOffer,
    LetterOptions,
    MatchList,
    OfferMatch,
    Queries,
    Result,
)

MIN_CHARS = 80


class InputError(ValueError):
    """CV ou offre inutilisable."""


class RecruitmentAgent:
    def __init__(self, llm: LLMClient, max_input_chars: int = 30_000):
        self.llm = llm
        self.max_input_chars = max_input_chars

    # -- validation --------------------------------------------------------
    def _prepare(self, label: str, text: str) -> str:
        text = (text or "").strip()
        if len(text) < MIN_CHARS:
            raise InputError(f"{label} trop court ou vide (minimum {MIN_CHARS} caractères).")
        if len(text) > self.max_input_chars:
            text = text[: self.max_input_chars]
        return text

    # -- étapes ------------------------------------------------------------
    def analyze(self, cv: str, offre: str, focus: str = "") -> Analysis:
        cv, offre = self._prepare("Le CV", cv), self._prepare("L'offre", offre)
        return self.llm.structured(
            prompts.ANALYSIS_SYSTEM,
            prompts.analysis_user(cv, offre, focus.strip()),
            Analysis,
            "submit_analysis",
        )

    def write_letter(
        self,
        cv: str,
        offre: str,
        analysis: Analysis,
        options: LetterOptions | None = None,
        *,
        previous: str | None = None,
        feedback: str | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> str:
        cv, offre = self._prepare("Le CV", cv), self._prepare("L'offre", offre)
        options = options or LetterOptions()
        return self.llm.text(
            prompts.LETTER_SYSTEM,
            prompts.letter_user(cv, offre, analysis, options, previous, feedback),
            on_delta,
        )

    def run(
        self,
        cv: str,
        offre: str,
        options: LetterOptions | None = None,
        on_step: Callable[[str], None] | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> Result:
        """Pipeline complet : analyse puis lettre."""
        step = on_step or (lambda _s: None)
        step("analyse")
        analysis = self.analyze(cv, offre)
        step("lettre")
        letter = self.write_letter(cv, offre, analysis, options, on_delta=on_delta)
        step("termine")
        return Result(analysis=analysis, letter=letter)


    # -- recherche d'offres ------------------------------------------------
    def suggest_queries(self, cv: str) -> list[str]:
        cv = self._prepare("Le CV", cv)
        q = self.llm.structured(prompts.QUERIES_SYSTEM, f"<cv>\n{cv}\n</cv>", Queries, "submit_queries")
        return [r.strip() for r in q.requetes if r.strip()][:4]

    def rank_offers(self, cv: str, offers: list[JobOffer], top: int = 10) -> list[tuple[JobOffer, OfferMatch]]:
        """Note chaque offre par rapport au CV (une seule requête au modèle) et trie par score."""
        if not offers:
            return []
        cv = self._prepare("Le CV", cv)
        batch = offers[:15]
        result = self.llm.structured(
            prompts.RANK_SYSTEM, prompts.rank_user(cv, batch), MatchList, "submit_matches"
        )
        by_id = {o.id: o for o in batch}
        ranked: dict[str, tuple[JobOffer, OfferMatch]] = {}
        for m in result.classement:
            if m.id in by_id and m.id not in ranked:
                ranked[m.id] = (by_id[m.id], m)
        for o in batch:  # offres oubliées par le modèle
            ranked.setdefault(o.id, (o, OfferMatch(id=o.id, score=0, raison="Non évaluée.")))
        return sorted(ranked.values(), key=lambda t: -t[1].score)[:top]

    # -- préparation d'entretien -------------------------------------------
    def prepare_interview(self, cv: str, offre: str, analysis: Analysis | None = None) -> InterviewPrep:
        cv, offre = self._prepare("Le CV", cv), self._prepare("L'offre", offre)
        return self.llm.structured(
            prompts.INTERVIEW_SYSTEM, prompts.interview_user(cv, offre, analysis), InterviewPrep, "submit_interview"
        )

    def evaluate_answer(self, cv: str, offre: str, question: InterviewQuestion, answer: str) -> AnswerFeedback:
        cv, offre = self._prepare("Le CV", cv), self._prepare("L'offre", offre)
        if len((answer or "").strip()) < 20:
            raise InputError("Réponse trop courte pour être évaluée.")
        return self.llm.structured(
            prompts.FEEDBACK_SYSTEM,
            prompts.feedback_user(cv, offre, question, answer.strip()),
            AnswerFeedback,
            "submit_feedback",
        )

    # -- e-mail de candidature ---------------------------------------------
    def draft_email(
        self,
        cv: str,
        *,
        entreprise: str = "",
        poste: str = "",
        langue: str = "français",
        offre: str | None = None,
        joint_lettre: bool = True,
    ) -> EmailDraft:
        cv = self._prepare("Le CV", cv)
        offre = offre.strip()[: self.max_input_chars] if offre and offre.strip() else None
        return self.llm.structured(
            prompts.EMAIL_SYSTEM,
            prompts.email_user(cv, offre, entreprise, poste, langue, joint_lettre),
            EmailDraft,
            "submit_email",
        )
