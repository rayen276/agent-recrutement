# ✉️ Agent RH — CV, offre d'emploi et lettre de motivation

Agent IA qui **analyse un CV, le compare à une offre d'emploi, rédige une lettre de motivation sur mesure**, cherche des offres, **prépare l'entretien** et rédige l'e-mail de candidature.

Propulsé par l'**API Groq** (palier gratuit, modèle `openai/gpt-oss-120b`). Gemini, OpenRouter et Claude sont aussi supportés.

![Aperçu de l'interface](docs/apercu-interface.png)

## Fonctionnalités

| | |
|---|---|
| 📄 **Analyse CV ↔ offre** | Score de correspondance sur 100, points forts, écarts, exigences couvertes / partielles / absentes, mots-clés, conseils pour améliorer le CV |
| ✍️ **Lettre de motivation** | Sur mesure, avec ton, langue et longueur réglables ; révisable (« plus court », « ajoute mon bénévolat »…) ; mots-clés de l'offre mis en évidence |
| 🔎 **Recherche d'offres** | Cherche des offres adaptées au CV (Remotive, Arbeitnow) et les classe par pertinence ; liens LinkedIn / Indeed |
| 🎤 **Préparation d'entretien** | Questions probables, pistes de réponse tirées du CV, questions à poser, **entraînement noté** avec version améliorée |
| 📧 **E-mail de candidature** | Brouillon avec pièces jointes ; **jamais envoyé sans votre confirmation** |
| 📦 **Export** | Markdown, Word (.docx), JSON, `.eml`, dossier ZIP complet |

**Principe de confiance** : la lettre ne s'appuie que sur les faits du CV (aucune expérience ni chiffre inventé), et rien n'est envoyé sans validation humaine. Relisez toujours avant d'envoyer.

## Démarrage rapide

### Option A — Python

```bash
git clone https://github.com/VOTRE-PSEUDO/agent-recrutement.git
cd agent-recrutement

python -m venv .venv
source .venv/bin/activate            # Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -e ".[web]"              # sans l'interface web (plus léger) : pip install -e .

cp .env.example .env                 # Windows : copy .env.example .env
# éditez .env et collez votre clé Groq (voir « Configuration »)

streamlit run app.py                 # interface web : http://localhost:8501
```

### Option B — Docker

```bash
cp .env.example .env                 # puis éditez .env
docker compose up --build            # interface web : http://localhost:8501
```

## Configuration

Copiez `.env.example` en `.env`, puis collez votre clé **Groq** (gratuite) :

1. Créez un compte et une clé sur [console.groq.com/keys](https://console.groq.com/keys).
2. Dans `.env` : `GROQ_API_KEY=votre-clé` (`RH_PROVIDER=groq` est la valeur par défaut).

Le fournisseur se change avec `RH_PROVIDER` :

| Fournisseur | `RH_PROVIDER` | Variable de clé | Coût |
|---|---|---|---|
| **Groq** | `groq` (défaut) | `GROQ_API_KEY` | palier gratuit, limites de débit |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | palier gratuit — [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | modèles `:free` disponibles |
| Anthropic (Claude) | `anthropic` | `ANTHROPIC_API_KEY` | payant — `pip install -e ".[anthropic]"` |

Autres variables : `RH_MODEL` (les noms de modèles évoluent), `RH_REASONING_EFFORT` (modèles gpt-oss), et `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` pour l'envoi d'e-mails (facultatif ; Gmail exige un « mot de passe d'application »).

> 🔒 **Ne publiez jamais votre `.env`** (il est ignoré par `.gitignore`).
>
> **Confidentialité** : sur les paliers gratuits, le fournisseur peut utiliser les textes envoyés pour améliorer ses produits. Anonymisez votre CV (nom, téléphone, adresse) si cela vous gêne.

## Utilisation

### Interface web

Renseignez le CV et l'offre, puis naviguez entre **Analyse CV & offre**, **Offres**, **Entretien** et **E-mail**. Le bouton « Exporter dossier » télécharge le rapport, la lettre et la fiche d'entretien dans une archive ZIP.

### Ligne de commande

```bash
# 1. Candidature : analyse + lettre
recruter candidater --cv examples/cv.txt --offre examples/offre.txt
recruter candidater --cv mon_cv.pdf --offre offre.docx --langue anglais --ton "formel et sobre" --mots 250

# 2. Offres : recherche + classement (mots-clés déduits du CV si --requete est omis)
recruter offres --cv mon_cv.pdf
recruter offres --cv mon_cv.pdf --requete "data analyst" --choisir 1     # candidature pour l'offre n°1

# 3. Entretien : fiche de questions (+ entraînement interactif)
recruter entretien --cv mon_cv.pdf --offre offre.txt --simuler

# 4. E-mail : brouillon seul, puis envoi après confirmation
recruter email --cv mon_cv.pdf --a recrutement@entreprise.com --entreprise Atlas --lettre sorties/lettre.docx
recruter email --cv mon_cv.pdf --a recrutement@entreprise.com --lettre sorties/lettre.docx --envoyer
```

Les résultats sont écrits dans `sorties/`. Avec Docker : déposez vos fichiers dans `donnees/` puis
`docker compose run --rm cli --cv /donnees/cv.txt --offre /donnees/offre.txt`.

### Comme bibliothèque Python

```python
from recruitment_agent import RecruitmentAgent, LetterOptions
from recruitment_agent.config import Settings
from recruitment_agent.llm import build_llm
from recruitment_agent.loaders import load_file

settings = Settings.from_env()
agent = RecruitmentAgent(build_llm(settings), settings.max_input_chars)
result = agent.run(load_file("cv.pdf"), load_file("offre.txt"), LetterOptions(langue="français"))
print(result.analysis.score)
print(result.letter)
```

## Architecture

```
src/recruitment_agent/
├── config.py       paramètres (.env, fournisseurs, budgets de jetons)
├── models.py       modèles Pydantic (Analysis, InterviewPrep, EmailDraft…)
├── loaders.py      lecture PDF / DOCX / TXT / MD
├── prompts.py      prompts (documents traités comme des données, anti-injection)
├── llm.py          interface LLM, client Claude, fabrique build_llm
├── llm_compat.py   client Groq / Gemini / OpenRouter (API compatible OpenAI, sans dépendance)
├── agent.py        orchestration : analyse, lettre, offres, entretien, e-mail
├── jobs.py         recherche d'offres (Remotive, Arbeitnow, liens manuels)
├── mailer.py       brouillon, validation, envoi SMTP avec confirmation
├── exporters.py    Markdown, Word, JSON, ZIP
├── ui.py           composants visuels de l'interface web
└── cli.py          commande `recruter`
app.py              interface Streamlit
tests/              tests unitaires (faux client LLM, aucun appel réseau)
```

Choix techniques :
- **Sortie structurée** : le schéma JSON est généré depuis des modèles Pydantic, puis la réponse est validée ; nouvelle tentative automatique si le JSON est invalide ou tronqué.
- **Résilience** : attente automatique quand le quota gratuit par minute est atteint, budgets de jetons par type de réponse, reprise de la lettre seule si elle échoue après l'analyse.
- **Testable** : l'agent dépend d'une interface `LLMClient` ; les tests utilisent un faux client.
- **Sécurité des e-mails** : validation de l'adresse, un destinataire par envoi, confirmation obligatoire, limite de 10 envois par session, protection contre l'injection d'en-têtes.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Dépannage

| Message | Cause et solution |
|---|---|
| `Clé API refusée (401/403)` | Clé invalide ou refusée : vérifiez `GROQ_API_KEY` dans `.env` (pas de guillemets, fichier enregistré), ou créez une nouvelle clé |
| `Modèle introuvable ou retiré (404)` | Le nom du modèle a changé : listez les modèles de votre compte (`https://api.groq.com/openai/v1/models`) et mettez à jour `RH_MODEL` |
| `Quota gratuit atteint (429)` | Limite par minute ou par jour : l'agent attend seul les délais courts ; sinon patientez, ou changez de modèle / fournisseur |
| `json_validate_failed` | Réponse du modèle tronquée : l'agent réessaie automatiquement avec plus de place |
| `Read timed out` pendant `docker compose build` | Connexion lente : relancez la commande (les paquets déjà téléchargés sont en cache) |
| `Envoi d'e-mail non configuré` | Renseignez les variables `SMTP_*` dans `.env`, ou téléchargez le brouillon `.eml` |

## Limites

- Les PDF scannés (images) ne sont pas lus : pas d'OCR.
- Les offres automatiques viennent de sources internationales (télétravail, Europe) et peuvent varier ; pour d'autres marchés, collez l'offre trouvée sur LinkedIn / Indeed.
- Le score est une estimation, pas une décision de recrutement : ne l'utilisez pas pour filtrer des candidats sans supervision humaine.
- Respectez les conditions d'utilisation des sites d'offres et n'utilisez pas l'envoi d'e-mails pour du démarchage de masse non sollicité.

## Pistes d'évolution

- OCR pour les CV scannés ; adaptation du CV lui-même à chaque offre ;
- sources d'offres locales ; suivi des candidatures et relances ;
- historique en base de données.

## Licence

MIT — voir [LICENSE](LICENSE).
