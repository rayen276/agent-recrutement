import pytest

from recruitment_agent.models import Analysis


class FakeLLM:
    """Faux client : aucune requête réseau."""

    def __init__(self):
        self.calls = []

    def structured(self, system, user, schema, tool_name):
        self.calls.append(("structured", user))
        name = getattr(schema, "__name__", "")
        if name == "Queries":
            return schema.model_validate({"requetes": ["digital marketing", "growth marketer", "  "]})
        if name == "MatchList":
            return schema.model_validate({"classement": [
                {"id": "2", "score": 85, "raison": "Très proche"},
                {"id": "1", "score": 40, "raison": "Partiel"},
                {"id": "99", "score": 100, "raison": "Id inconnu"},
            ]})
        if name == "InterviewPrep":
            return schema.model_validate({
                "questions": [{"categorie": "technique", "question": "Parlez de GA4", "objectif": "Niveau", "piste_reponse": "Certification GA4"}],
                "questions_a_poser": ["Quelle équipe ?"], "conseils": ["Préparez des chiffres"]})
        if name == "AnswerFeedback":
            return schema.model_validate({"note": 7, "points_forts": ["Concret"], "a_ameliorer": ["Chiffres"], "version_amelioree": "Version."})
        if name == "EmailDraft":
            return schema.model_validate({"objet": "Candidature\nInjection", "corps": "Bonjour,\n\nCordialement"})
        return Analysis.model_validate(
            {
                "poste": "Responsable Acquisition",
                "entreprise": "Maison Atlas",
                "score": 72,
                "resume": "Profil solide, manque d'expérience en management.",
                "points_forts": [{"titre": "Google Ads", "preuve": "12 clients PME"}],
                "ecarts": [{"titre": "Management", "detail": "Aucune équipe encadrée", "conseil": "Citer le mentorat"}],
                "exigences": [{"exigence": "GA4", "statut": "couvert", "commentaire": "Certifiée GA4"}],
                "mots_cles": {"presents": ["GA4"], "manquants": ["TikTok Ads"]},
                "conseils_cv": ["Ajouter TikTok Ads"],
                "angle_lettre": "Résultats chiffrés en e-commerce",
                "nom_candidat": "Sarra Ben Ali",
            }
        )

    def text(self, system, user, on_delta=None):
        self.calls.append(("text", user))
        letter = "Madame, Monsieur,\n\nMa candidature.\n\nSarra Ben Ali"
        if on_delta:
            on_delta(letter)
        return letter


@pytest.fixture
def fake_llm():
    return FakeLLM()


LONG_CV = "Expérience en marketing digital. " * 10
LONG_OFFRE = "Nous recherchons un responsable acquisition. " * 10
