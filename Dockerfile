# syntax=docker/dockerfile:1
# Image : interface web Streamlit + commande `recruter`
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Miroir PyPI facultatif : docker compose build --build-arg PIP_INDEX_URL=https://...
ARG PIP_INDEX_URL=""

WORKDIR /app

# 1) Dépendances d'abord : cette couche n'est refaite que si requirements-docker.txt change.
#    Délais longs + nouvelles tentatives pour les connexions lentes ; le cache pip survit aux échecs
#    (les paquets déjà téléchargés ne sont pas retéléchargés au prochain essai).
COPY requirements-docker.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=300 --retries 10 ${PIP_INDEX_URL:+--index-url $PIP_INDEX_URL} \
    -r requirements-docker.txt

# 2) Code ensuite : modifier src/ ne retélécharge plus rien
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-deps .

COPY app.py ./
COPY .streamlit ./.streamlit
COPY examples ./examples

# Utilisateur non-root + dossier de sortie
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/sorties \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).status == 200 else 1)"

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
