"""Interface en ligne de commande.

    recruter candidater --cv cv.pdf --offre offre.txt     analyse + lettre
    recruter offres     --cv cv.pdf                       cherche et classe des offres
    recruter entretien  --cv cv.pdf --offre offre.txt     questions + entraînement
    recruter email      --cv cv.pdf --a rh@exemple.com    brouillon (et envoi sur demande)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import InputError, RecruitmentAgent
from .config import ConfigError, Settings
from .exporters import (
    interview_docx_bytes,
    interview_markdown,
    report_markdown,
    save_all,
)
from .jobs import manual_search_links, search_jobs
from .llm import LLMError, build_llm
from .loaders import LoaderError, load_file
from .mailer import MailError, SmtpSettings, build_message, send, to_eml, validate_address
from .models import LetterOptions, Result

COMMANDS = {"candidater", "offres", "entretien", "email"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="recruter", description="Agent RH : candidature, offres, entretien, e-mail.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("candidater", help="Analyse un CV face à une offre et rédige la lettre")
    c.add_argument("--cv", required=True)
    c.add_argument("--offre", required=True)
    c.add_argument("--sortie", default="sorties")
    c.add_argument("--ton", default="professionnel et chaleureux")
    c.add_argument("--langue", default="français")
    c.add_argument("--mots", type=int, default=300, help="Longueur cible de la lettre (100-700)")
    c.add_argument("--consigne", default="")
    c.add_argument("--analyse-seule", action="store_true", help="Ne pas rédiger la lettre")

    o = sub.add_parser("offres", help="Cherche des offres et les classe selon votre CV")
    o.add_argument("--cv", required=True)
    o.add_argument("--requete", action="append", help="Mot-clé de recherche (répétable). Sinon : déduit du CV")
    o.add_argument("--lieu", default="", help="Lieu pour les liens de recherche manuelle")
    o.add_argument("--top", type=int, default=8)
    o.add_argument("--choisir", type=int, help="Numéro d'une offre : lance l'analyse et la lettre pour elle")
    o.add_argument("--sortie", default="sorties")

    e = sub.add_parser("entretien", help="Génère les questions probables ; --simuler pour s'entraîner")
    e.add_argument("--cv", required=True)
    e.add_argument("--offre", required=True)
    e.add_argument("--sortie", default="sorties")
    e.add_argument("--simuler", action="store_true", help="Entretien interactif avec retour sur vos réponses")

    m = sub.add_parser("email", help="Rédige un e-mail de candidature (aperçu ; envoi avec --envoyer)")
    m.add_argument("--cv", required=True, help="CV, joint à l'e-mail")
    m.add_argument("--a", required=True, help="Adresse du destinataire")
    m.add_argument("--entreprise", default="")
    m.add_argument("--poste", default="")
    m.add_argument("--offre", help="Fichier de l'offre (facultatif, améliore l'e-mail)")
    m.add_argument("--lettre", help="Lettre de motivation à joindre (.docx, .pdf…)")
    m.add_argument("--langue", default="français")
    m.add_argument("--sortie", default="sorties")
    m.add_argument("--envoyer", action="store_true", help="Envoie réellement l'e-mail (après confirmation)")
    m.add_argument("--oui", action="store_true", help="Confirme l'envoi sans question")
    return p


def _normalize_argv(argv: list[str]) -> list[str]:
    """Compatibilité : `recruter --cv … --offre …` équivaut à `recruter candidater …`."""
    if argv and argv[0] not in COMMANDS and argv[0] not in ("-h", "--help"):
        return ["candidater", *argv]
    return argv


def _agent() -> RecruitmentAgent:
    settings = Settings.from_env()
    llm = build_llm(settings)
    if hasattr(llm, "on_wait"):
        llm.on_wait = lambda sec: _info(f"⏳ Quota gratuit atteint : nouvelle tentative dans {int(sec) + 1} s…")
    return RecruitmentAgent(llm, settings.max_input_chars)


def _info(msg: str = "") -> None:
    print(msg, file=sys.stderr)


# -- commandes -------------------------------------------------------------
def cmd_candidater(a: argparse.Namespace, agent: RecruitmentAgent | None = None, offre_text: str | None = None) -> int:
    agent = agent or _agent()
    cv = load_file(a.cv)
    offre = offre_text if offre_text is not None else load_file(a.offre)
    options = LetterOptions(ton=a.ton, langue=a.langue, longueur_mots=a.mots, consigne=a.consigne)

    _info("▶ Analyse du CV et de l'offre…")
    analysis = agent.analyze(cv, offre)
    print(report_markdown(analysis))
    letter = ""
    if not a.analyse_seule:
        _info("\n▶ Rédaction de la lettre…\n")
        letter = agent.write_letter(cv, offre, analysis, options, on_delta=lambda d: print(d, end="", flush=True))
        print()
    paths = save_all(Result(analysis=analysis, letter=letter), Path(a.sortie))
    if a.analyse_seule:
        for name in ("lettre.md", "lettre.docx"):
            paths.pop(name).unlink(missing_ok=True)
    _info("\n✔ Fichiers enregistrés :")
    for path in paths.values():
        _info(f"  - {path}")
    return 0


def cmd_offres(a: argparse.Namespace) -> int:
    agent = _agent()
    cv = load_file(a.cv)
    queries = a.requete or agent.suggest_queries(cv)
    _info(f"▶ Recherche : {', '.join(queries)}")
    offers, errors = search_jobs(queries)
    for err in errors:
        _info(f"⚠ Source indisponible : {err}")

    print("\nRecherche manuelle (à ouvrir dans le navigateur) :")
    for name, url in manual_search_links(queries[0], a.lieu).items():
        print(f"  - {name} : {url}")
    if not offers:
        _info("\nAucune offre trouvée par les sources automatiques. Utilisez les liens ci-dessus, puis "
              "`recruter candidater` avec le texte de l'offre.")
        return 0

    _info("\n▶ Classement selon votre CV…")
    ranked = agent.rank_offers(cv, offers, top=a.top)
    print()
    for i, (job, m) in enumerate(ranked, 1):
        print(f"[{i}] {m.score:>3}%  {job.titre} — {job.entreprise} ({job.lieu})")
        print(f"      {m.raison}")
        print(f"      {job.url}  [{job.source}]\n")

    if a.choisir:
        if not 1 <= a.choisir <= len(ranked):
            raise InputError(f"--choisir doit être entre 1 et {len(ranked)}.")
        job = ranked[a.choisir - 1][0]
        _info(f"\n▶ Candidature pour : {job.titre} — {job.entreprise}\n")
        ns = argparse.Namespace(
            cv=a.cv, offre=None, sortie=a.sortie, ton="professionnel et chaleureux",
            langue="français", mots=300, consigne="", analyse_seule=False,
        )
        return cmd_candidater(ns, agent, offre_text=job.as_text())
    _info("Astuce : ajoutez --choisir N pour lancer l'analyse et la lettre de l'offre N.")
    return 0


def cmd_entretien(a: argparse.Namespace) -> int:
    agent = _agent()
    cv, offre = load_file(a.cv), load_file(a.offre)
    _info("▶ Préparation de l'entretien…")
    prep = agent.prepare_interview(cv, offre)
    md = interview_markdown(prep)
    out = Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    (out / "entretien.md").write_text(md, encoding="utf-8")
    (out / "entretien.docx").write_bytes(interview_docx_bytes(prep))
    print(md)
    _info(f"✔ Enregistré : {out / 'entretien.md'} et {out / 'entretien.docx'}")

    if a.simuler:
        _info("\n=== Simulation d'entretien (réponse vide ou « q » pour quitter) ===")
        for i, q in enumerate(prep.questions, 1):
            print(f"\nQuestion {i}/{len(prep.questions)} [{q.categorie}] : {q.question}")
            answer = input("Votre réponse > ").strip()
            if answer.lower() in {"", "q"}:
                break
            try:
                fb = agent.evaluate_answer(cv, offre, q, answer)
            except InputError as exc:
                print(f"  {exc}")
                continue
            print(f"\n  Note : {fb.note}/10")
            print("  Points forts : " + "; ".join(fb.points_forts))
            print("  À améliorer  : " + "; ".join(fb.a_ameliorer))
            print(f"  Version améliorée : {fb.version_amelioree}")
    return 0


def cmd_email(a: argparse.Namespace) -> int:
    validate_address(a.a)  # avant tout appel au modèle : inutile de consommer du quota pour rien
    agent = _agent()
    cv = load_file(a.cv)
    offre = load_file(a.offre) if a.offre else None
    _info("▶ Rédaction de l'e-mail…")
    draft = agent.draft_email(
        cv, entreprise=a.entreprise, poste=a.poste, langue=a.langue, offre=offre, joint_lettre=bool(a.lettre)
    )
    attachments = [(Path(a.cv).name, Path(a.cv).read_bytes())]
    if a.lettre:
        attachments.append((Path(a.lettre).name, load_bytes_raw(a.lettre)))

    smtp: SmtpSettings | None = None
    if a.envoyer:
        smtp = SmtpSettings.from_env()
    msg = build_message(a.a, draft.objet, draft.corps, attachments, sender=smtp.sender if smtp else None)

    out = Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    eml = out / "email.eml"
    eml.write_bytes(to_eml(msg))
    print(f"À      : {a.a}\nObjet  : {msg['Subject']}\nPièces : {', '.join(n for n, _ in attachments)}\n\n{draft.corps}\n")
    _info(f"✔ Brouillon enregistré : {eml}")

    if not a.envoyer:
        _info("Aucun e-mail envoyé. Relisez, puis relancez avec --envoyer pour l'expédier.")
        return 0
    if not a.oui:
        if input(f"Envoyer cet e-mail à {a.a} ? (oui/non) > ").strip().lower() not in {"oui", "o", "yes", "y"}:
            _info("Envoi annulé.")
            return 0
    send(smtp, msg)
    _info("✔ E-mail envoyé.")
    return 0


def load_bytes_raw(path: str) -> bytes:
    p = Path(path)
    if not p.is_file():
        raise LoaderError(f"Fichier introuvable : {p}")
    return p.read_bytes()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(_normalize_argv(list(sys.argv[1:] if argv is None else argv)))
    try:
        return {"candidater": cmd_candidater, "offres": cmd_offres, "entretien": cmd_entretien, "email": cmd_email}[
            args.cmd
        ](args)
    except (ConfigError, LoaderError, InputError, LLMError, MailError) as exc:
        _info(f"Erreur : {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        _info("\nInterrompu.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
