"""Recherche d'offres via des API publiques gratuites (sans clé) : Remotive et Arbeitnow.

Ces sources couvrent surtout le télétravail et l'Europe. Pour la Tunisie, utilisez aussi les liens
de recherche manuelle (LinkedIn, Indeed) et collez l'offre trouvée dans l'application.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .models import JobOffer

USER_AGENT = "recruitment-agent/1.0 (recherche d'emploi personnelle)"


class JobSearchError(RuntimeError):
    """Une source d'offres est indisponible."""


def get_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise JobSearchError(f"{urllib.parse.urlparse(url).netloc} : {exc}") from exc


def strip_html(raw: str, limit: int = 4000) -> str:
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return text[:limit]


def _tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]


def search_remotive(query: str, limit: int = 10) -> list[JobOffer]:
    url = "https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": query, "limit": limit})
    jobs = get_json(url).get("jobs", [])
    return [
        JobOffer(
            id="",
            titre=j.get("title", ""),
            entreprise=j.get("company_name", ""),
            lieu=j.get("candidate_required_location", "") or "Télétravail",
            url=j.get("url", ""),
            source="Remotive",
            date=str(j.get("publication_date", ""))[:10],
            description=strip_html(j.get("description", "")),
        )
        for j in jobs[:limit]
    ]


def search_arbeitnow(query: str, limit: int = 10) -> list[JobOffer]:
    """Arbeitnow n'a pas de paramètre de recherche : on filtre localement la première page."""
    data = get_json("https://www.arbeitnow.com/api/job-board-api").get("data", [])
    tokens = _tokens(query)
    scored: list[tuple[int, dict]] = []
    for j in data:
        hay = " ".join([j.get("title", ""), " ".join(j.get("tags", []) or [])]).lower()
        score = sum(t in hay for t in tokens)
        if score:
            scored.append((score, j))
    scored.sort(key=lambda x: -x[0])
    offers = []
    for _, j in scored[:limit]:
        created = j.get("created_at")
        date = ""
        if isinstance(created, (int, float)):
            date = datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d")
        offers.append(
            JobOffer(
                id="",
                titre=j.get("title", ""),
                entreprise=j.get("company_name", ""),
                lieu=("Télétravail · " if j.get("remote") else "") + (j.get("location", "") or ""),
                url=j.get("url", ""),
                source="Arbeitnow",
                date=date,
                description=strip_html(j.get("description", "")),
            )
        )
    return offers


SOURCES = {"remotive": search_remotive, "arbeitnow": search_arbeitnow}


def search_jobs(
    queries: list[str],
    sources: tuple[str, ...] = ("remotive", "arbeitnow"),
    per_query: int = 8,
    total: int = 15,
) -> tuple[list[JobOffer], list[str]]:
    """Interroge les sources pour chaque requête. Renvoie (offres dédoublonnées, erreurs)."""
    seen: set[str] = set()
    offers: list[JobOffer] = []
    errors: list[str] = []
    for q in queries:
        for name in sources:
            try:
                found = SOURCES[name](q, per_query)
            except JobSearchError as exc:
                msg = str(exc)
                if msg not in errors:
                    errors.append(msg)
                continue
            for o in found:
                key = o.url or f"{o.titre}|{o.entreprise}"
                if key in seen or not o.titre:
                    continue
                seen.add(key)
                offers.append(o)
    offers = offers[:total]
    for i, o in enumerate(offers, 1):
        o.id = str(i)
    return offers, errors


def manual_search_links(query: str, location: str = "") -> dict[str, str]:
    """Liens de recherche à ouvrir dans le navigateur (pas d'API gratuite pour ces sites)."""
    q, loc = urllib.parse.quote_plus(query), urllib.parse.quote_plus(location)
    return {
        "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}",
        "Indeed": f"https://www.indeed.com/jobs?q={q}&l={loc}",
    }
