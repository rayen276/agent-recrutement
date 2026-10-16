"""Modèles de données (validation Pydantic)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Strength(BaseModel):
    titre: str = Field(description="Point fort, en quelques mots")
    preuve: str = Field(description="Élément concret du CV qui l'illustre")


class Gap(BaseModel):
    titre: str
    detail: str = Field(description="Ce qui manque ou est insuffisant par rapport à l'offre")
    conseil: str = Field(description="Comment le compenser ou le présenter")


class Requirement(BaseModel):
    exigence: str = Field(description="Exigence importante de l'offre")
    statut: Literal["couvert", "partiel", "absent"]
    commentaire: str


class Keywords(BaseModel):
    presents: list[str] = Field(default_factory=list, description="Mots-clés de l'offre présents dans le CV")
    manquants: list[str] = Field(default_factory=list, description="Mots-clés de l'offre absents du CV")


class Analysis(BaseModel):
    """Résultat de la comparaison CV / offre."""

    poste: str = Field(description="Intitulé du poste")
    entreprise: str = Field(default="", description="Nom de l'entreprise si connu, sinon chaîne vide")
    score: int = Field(ge=0, le=100, description="Score de correspondance réaliste de 0 à 100")
    resume: str = Field(description="Synthèse honnête en 2 phrases")
    points_forts: list[Strength] = Field(description="3 à 5 points forts")
    ecarts: list[Gap] = Field(default_factory=list, description="0 à 4 écarts")
    exigences: list[Requirement] = Field(description="4 à 8 exigences clés de l'offre")
    mots_cles: Keywords
    conseils_cv: list[str] = Field(description="3 à 5 actions concrètes pour améliorer le CV")
    angle_lettre: str = Field(description="L'angle le plus convaincant pour la lettre de motivation")
    nom_candidat: str = Field(default="", description="Nom du candidat s'il figure dans le CV")


class LetterOptions(BaseModel):
    ton: str = "professionnel et chaleureux"
    longueur_mots: int = Field(default=300, ge=100, le=700)
    langue: str = "français"
    consigne: str = ""


class Result(BaseModel):
    analysis: Analysis
    letter: str


# --------------------------------------------------------------------------
# Recherche d'offres
# --------------------------------------------------------------------------
class JobOffer(BaseModel):
    id: str
    titre: str
    entreprise: str = ""
    lieu: str = ""
    url: str = ""
    source: str = ""
    date: str = ""
    description: str = ""

    def as_text(self) -> str:
        """Texte utilisable comme « offre » dans le pipeline de candidature."""
        head = " — ".join(x for x in (self.titre, self.entreprise, self.lieu) if x)
        return f"{head}\n\n{self.description}".strip()


class Queries(BaseModel):
    requetes: list[str] = Field(
        description="2 à 4 requêtes courtes de recherche d'emploi (intitulés de poste de 1 à 3 mots)"
    )


class OfferMatch(BaseModel):
    id: str = Field(description="Identifiant de l'offre, tel que fourni")
    score: int = Field(ge=0, le=100, description="Adéquation CV/offre, de 0 à 100")
    raison: str = Field(description="Une phrase : pourquoi cette note")


class MatchList(BaseModel):
    classement: list[OfferMatch]


# --------------------------------------------------------------------------
# Préparation d'entretien
# --------------------------------------------------------------------------
class InterviewQuestion(BaseModel):
    categorie: str = Field(
        description="présentation, motivation, technique, comportementale, points faibles ou mise en situation"
    )
    question: str
    objectif: str = Field(description="Ce que le recruteur cherche à évaluer")
    piste_reponse: str = Field(
        description="Piste de réponse en 2 à 3 phrases, fondée UNIQUEMENT sur le CV (méthode STAR pour les comportementales)"
    )


class InterviewPrep(BaseModel):
    questions: list[InterviewQuestion] = Field(description="8 à 10 questions probables")
    questions_a_poser: list[str] = Field(description="3 à 5 questions pertinentes à poser au recruteur")
    conseils: list[str] = Field(description="3 à 5 conseils personnalisés")


class AnswerFeedback(BaseModel):
    note: int = Field(ge=0, le=10)
    points_forts: list[str]
    a_ameliorer: list[str]
    version_amelioree: str = Field(description="Réponse améliorée, fondée uniquement sur le CV")


# --------------------------------------------------------------------------
# E-mail de candidature
# --------------------------------------------------------------------------
class EmailDraft(BaseModel):
    objet: str
    corps: str
