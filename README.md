# Agent RH — CV, offre d'emploi et lettre de motivation

Agent IA (Python, Gemini gratuit ou Claude) qui :

1. **lit** un CV et une offre (PDF, DOCX, TXT, MD) ;
2. **compare** les deux : score sur 100, points forts, écarts, exigences couvertes/partielles/absentes, mots-clés, conseils pour le CV ;
3. **rédige** une lettre de motivation adaptée (ton, langue, longueur réglables), révisable à la demande ;
4. **exporte** le tout en Markdown, Word et JSON ;
5. **cherche des offres** adaptées au CV et les classe par pertinence ;
6. **prépare l'entretien** : questions probables, pistes de réponse, questions à poser, et entraînement avec évaluation de vos réponses ;
7. **rédige un e-mail de candidature** et l'envoie, uniquement après votre relecture et votre confirmation.

La lettre ne s'appuie que sur les faits du CV : le prompt interdit d'inventer des expériences ou des chiffres. Relisez-la avant envoi.

## Installation (100 % gratuit avec Gemini)

L'agent fonctionne avec un fournisseur **gratuit, sans carte bancaire** : l'API Gemini de Google (palier gratuit d'AI Studio). Groq (gratuit) et OpenRouter sont aussi supportés ; Claude (payant) reste disponible.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
pip install -e .                   # léger ; interface web : pip install -e ".[web]"
cp .env.example .env               # Windows : copy .env.example .env
```

1. Créez une clé sur https://aistudio.google.com/apikey (connexion avec un compte Google).
2. Ouvrez `.env` et remplacez `colle-ta-cle-ici` par la clé, puis enregistrez.

| Fournisseur | `RH_PROVIDER` | Clé | Coût |
|---|---|---|---|
| Google Gemini | `gemini` (défaut) | `GEMINI_API_KEY` | palier gratuit avec limites de débit |
| Groq | `groq` | `GROQ_API_KEY` | palier gratuit |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | modèles `:free` disponibles |
| Anthropic (Claude) | `anthropic` | `ANTHROPIC_API_KEY` | payant (`pip install -e ".[anthropic]"`) |

Le modèle se change avec `RH_MODEL` (les noms évoluent : en cas d'erreur 404, lisez le message, Google y indique le modèle à utiliser).

**Confidentialité** : sur le palier gratuit de Gemini, Google peut utiliser les contenus envoyés pour améliorer ses produits. Évitez d'y envoyer des documents confidentiels ; anonymisez au besoin (nom, téléphone, adresse).

## Docker

Aucune installation de Python n'est nécessaire : seul [Docker](https://www.docker.com/products/docker-desktop/) l'est.

```bash
cp .env.example .env               # Windows : copy .env.example .env
# éditez .env : GEMINI_API_KEY=votre-clé  (gratuite : https://aistudio.google.com/apikey)

docker compose up --build          # interface web sur http://localhost:8501
docker compose down                # arrêt
```

Ligne de commande dans le conteneur (déposez vos fichiers dans `donnees/`, les résultats arrivent dans `sorties/`) :

```bash
docker compose run --rm cli --cv /donnees/cv.txt --offre /donnees/offre.txt
docker compose run --rm cli --cv /donnees/mon_cv.pdf --offre /donnees/offre.docx --langue anglais
```

Sans Compose :

```bash
docker build -t agent-recrutement .
docker run --rm -p 8501:8501 --env-file .env agent-recrutement
```

**Connexion lente ou erreur « Read timed out » pendant `docker compose up --build`** : relancez simplement la commande. Les dépendances sont installées avant le code, avec des délais longs et un cache : les paquets déjà téléchargés ne sont pas retéléchargés, et modifier le code ne réinstalle rien. Pour suivre l'avancement : `docker compose build --progress=plain`. Si votre réseau bloque PyPI, indiquez un miroir : `docker compose build --build-arg PIP_INDEX_URL=https://votre-miroir/simple`. Alternative sans Docker : environnement virtuel Python (voir Installation), sans l'option `[web]` pour la ligne de commande seule.

Notes : le fichier `.env` n'est pas copié dans l'image (il est lu au lancement) ; le conteneur tourne en utilisateur non-root ; l'image fait quelques centaines de Mo à cause de Streamlit (prévoyez de l'espace disque).

## Utilisation

### Ligne de commande

```bash
# 1. Candidature : analyse + lettre
recruter candidater --cv examples/cv.txt --offre examples/offre.txt
recruter candidater --cv mon_cv.pdf --offre offre.docx --langue anglais --ton "formel et sobre" --mots 250
#    (l'ancienne forme « recruter --cv … --offre … » fonctionne toujours)

# 2. Offres : recherche + classement selon le CV (mots-clés déduits du CV si --requete est omis)
recruter offres --cv mon_cv.pdf
recruter offres --cv mon_cv.pdf --requete "data analyst" --requete "BI" --choisir 1   # lance la candidature pour l'offre n°1

# 3. Entretien : fiche de questions (+ entraînement interactif avec --simuler)
recruter entretien --cv mon_cv.pdf --offre offre.txt
recruter entretien --cv mon_cv.pdf --offre offre.txt --simuler

# 4. E-mail : brouillon seul (rien n'est envoyé) puis envoi après confirmation
recruter email --cv mon_cv.pdf --a recrutement@entreprise.com --entreprise Atlas --poste "Growth" --lettre sorties/lettre.docx
recruter email --cv mon_cv.pdf --a recrutement@entreprise.com --entreprise Atlas --lettre sorties/lettre.docx --envoyer
```

Les fichiers sont écrits dans `sorties/` (`analyse.json`, `rapport.md|docx`, `lettre.md|docx`, `entretien.md|docx`, `email.eml`).

### Interface web

```bash
streamlit run app.py      # ou : docker compose up --build
```

Le CV et l'offre se renseignent dans la barre latérale. Quatre onglets : **Candidature**, **Offres** (le bouton « Utiliser cette offre » remplit la barre latérale), **Entretien** (questions + entraînement noté) et **E-mail** (brouillon, téléchargement `.eml`, envoi après confirmation).

Le thème (page claire pleine largeur, cartes blanches, accent violet) vient de `.streamlit/config.toml` et de `src/recruitment_agent/ui.py`. Après une modification de `ui.py`, redémarrez Streamlit (le module reste en mémoire). Le bouton « Exporter dossier » de l'en-tête télécharge une archive ZIP (rapport, lettre, fiche d'entretien).

### Recherche d'offres : sources et limites

Les sources automatiques sont des API publiques gratuites sans clé : **Remotive** (télétravail) et **Arbeitnow** (Europe). Elles couvrent peu la Tunisie : l'agent affiche donc aussi des liens de recherche **LinkedIn** et **Indeed** ; copiez l'offre trouvée dans la barre latérale. Respectez les conditions d'utilisation de ces sites (pas de collecte massive).

### E-mails : sécurité

- Aucun envoi sans votre confirmation explicite (case à cocher dans l'interface, question `oui/non` en ligne de commande).
- Un seul destinataire par envoi, adresse validée, limite de 10 envois par session web, protection contre l'injection d'en-têtes.
- L'agent n'invente aucune adresse : c'est vous qui fournissez le destinataire. N'utilisez pas l'outil pour de l'envoi en masse non sollicité.
- Configuration SMTP dans `.env` (voir `.env.example`). Gmail exige un « mot de passe d'application ». Sans SMTP, téléchargez le brouillon `.eml` et envoyez-le depuis votre messagerie.

### En tant que bibliothèque

```python
from recruitment_agent import RecruitmentAgent, LetterOptions
from recruitment_agent.config import Settings
from recruitment_agent.llm import AnthropicLLM
from recruitment_agent.loaders import load_file

settings = Settings.from_env()
agent = RecruitmentAgent(AnthropicLLM(settings))
result = agent.run(load_file("cv.pdf"), load_file("offre.txt"), LetterOptions(langue="français"))
print(result.analysis.score, result.letter)
```

## Architecture

```
src/recruitment_agent/
├── config.py     paramètres (.env, modèle, limites)
├── models.py     modèles Pydantic (Analysis, LetterOptions, Result)
├── loaders.py    lecture PDF / DOCX / TXT / MD
├── prompts.py    prompts système et utilisateur
├── llm.py        interface LLM + client Claude (SDK) + fabrique `build_llm`
├── llm_compat.py client Gemini / Groq / OpenRouter (API compatible OpenAI, sans dépendance)
├── agent.py      orchestration analyse → lettre (+ révisions)
├── jobs.py       recherche d'offres (Remotive, Arbeitnow, liens manuels)
├── mailer.py     brouillon, validation, envoi SMTP (avec confirmation)
├── ui.py         composants visuels de l'interface web (CSS + HTML échappé)
├── exporters.py  Markdown, Word, JSON (rapport, lettre, fiche d'entretien)
└── cli.py        commande `recruter` (candidater, offres, entretien, email)
app.py            interface Streamlit
Dockerfile, docker-compose.yml, .dockerignore   conteneurisation
donnees/          fichiers d'entrée pour le mode Docker CLI
tests/            tests unitaires (faux client LLM, aucun appel réseau)
```

- **Sortie fiable** : le schéma JSON est généré depuis `Analysis` (appel d'outil forcé avec Claude, mode JSON sinon), puis validé par Pydantic avec une nouvelle tentative en cas de JSON invalide.
- **Testable** : `RecruitmentAgent` dépend d'une interface `LLMClient` ; les tests utilisent un faux client.
- **Sécurité** : CV et offre sont encadrés par des balises et traités comme des données (défense contre l'injection de prompt) ; texte tronqué à 30 000 caractères par document.

## Tests

```bash
pytest
```

## Pistes d'évolution

- OCR pour les CV scannés ; adaptation du CV lui-même à l'offre ;
- sources d'offres locales (Tunisie) si une API publique devient disponible ;
- suivi des candidatures (envoyées, relances) ; historique en base.

## Limites

- Les modèles gratuits peuvent tronquer ou mal formater une longue réponse : l'agent redemande automatiquement avec plus de place (jusqu'à 3 essais) et attend si le quota par minute est atteint.
- Les PDF scannés (images) ne sont pas lus sans OCR.
- Les offres automatiques viennent de sources internationales ; les résultats varient et les API peuvent changer.
- Le score est une estimation, pas une décision de recrutement : ne l'utilisez pas pour filtrer des candidats sans supervision humaine.
