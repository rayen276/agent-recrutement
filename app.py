"""Interface web Streamlit : `streamlit run app.py`.

En-tête (navigation + export), cartes CV / offre, puis la vue choisie :
analyse + lettre, recherche d'offres, préparation d'entretien, e-mail de candidature.
"""

from __future__ import annotations

import time

import streamlit as st

from recruitment_agent import ui
from recruitment_agent.agent import InputError, RecruitmentAgent
from recruitment_agent.config import ConfigError, Settings
from recruitment_agent.exporters import (
    export_zip,
    interview_docx_bytes,
    interview_markdown,
    letter_docx_bytes,
    report_docx_bytes,
    report_markdown,
)
from recruitment_agent.jobs import manual_search_links, search_jobs
from recruitment_agent.llm import LLMError, build_llm
from recruitment_agent.loaders import LoaderError, load_bytes
from recruitment_agent.mailer import (
    MAX_SENDS_PER_SESSION,
    MailError,
    SmtpSettings,
    build_message,
    send,
    to_eml,
)
from recruitment_agent.models import LetterOptions

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
NAV = ["Analyse CV & offre", "Offres", "Entretien", "E-mail"]
LANGS = ["français", "anglais", "arabe", "espagnol", "allemand"]
FOCUS = {"Équilibrée": "", "Compétences techniques": "compétences techniques et outils", "Parcours & projets": "parcours, réalisations et projets"}

st.set_page_config(page_title="Agent RH", page_icon="✉️", layout="wide", initial_sidebar_state="collapsed")
st.markdown(ui.CSS, unsafe_allow_html=True)


def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


@st.cache_resource
def get_runtime() -> tuple[Settings, RecruitmentAgent]:
    settings = Settings.from_env()
    return settings, RecruitmentAgent(build_llm(settings), settings.max_input_chars)


def read_input(label: str, key: str):
    """Import de fichier + zone de texte ; le fichier prime. Renvoie (texte, nom_fichier, octets)."""
    up = st.file_uploader(label, type=["pdf", "docx", "txt", "md"], key=f"{key}_file", label_visibility="collapsed")
    text = st.text_area("Ou collez le texte ici", height=150, key=f"{key}_text")
    if up is not None:
        data = up.getvalue()
        try:
            content = load_bytes(up.name, data)
        except LoaderError as exc:
            st.error(str(exc))
            return "", None, None
        return content, up.name, data
    return text, None, None


def use_offer(text: str) -> None:
    """Callback : place l'offre choisie dans la carte « offre » et revient à l'analyse."""
    st.session_state["offre_text"] = text
    st.session_state["offer_imported"] = True
    st.session_state["nav"] = NAV[0]


def rewrite_letter(agent_, cv_, offre_, analysis_, options_) -> None:
    """Callback du bouton « Réécrire » (peut modifier l'état du champ lettre)."""
    feedback = (st.session_state.get("rev_text") or "").strip()
    if not feedback:
        return
    try:
        st.session_state["letter_edit"] = agent_.write_letter(
            cv_, offre_, analysis_, options_, previous=st.session_state.get("letter_edit", ""), feedback=feedback
        )
        st.session_state["rev_text"] = ""
    except (InputError, LLMError) as exc:
        st.session_state["rev_error"] = str(exc)


def guard(fn):
    """Exécute fn en affichant proprement les erreurs attendues."""
    try:
        return fn()
    except (InputError, LLMError, MailError, ConfigError) as exc:
        st.error(str(exc))
        return None


try:
    settings, agent = get_runtime()
except ConfigError as exc:
    with st.container(key="content"):
        st.error(str(exc))
    st.stop()

if hasattr(agent.llm, "on_wait"):
    agent.llm.on_wait = lambda sec: st.write(f"⏳ Quota gratuit atteint : nouvelle tentative automatique dans {int(sec) + 1} s…")

analysis = st.session_state.get("analysis")
current_letter = st.session_state.get("letter_edit") or st.session_state.get("letter", "")

# ===========================================================================
# En-tête
# ===========================================================================
with st.container(key="hdr"):
    h1, h2, h3, h4 = st.columns([2.7, 4.9, 1.5, 1.7])
    with h1:
        html(ui.brand())
    with h2:
        with st.container(key="navbox"):
            st.radio("Navigation", NAV, horizontal=True, key="nav", label_visibility="collapsed")
            nav = st.session_state["nav"]
    with h3:
        html(ui.status_pill(settings.model))
    with h4:
        zip_bytes = export_zip(analysis, current_letter, st.session_state.get("prep"))
        st.download_button(
            "⬇ Exporter dossier", zip_bytes or b"", "dossier-candidature.zip", "application/zip",
            type="primary", disabled=not zip_bytes, use_container_width=True,
        )

# ===========================================================================
# Contenu
# ===========================================================================
with st.container(key="content"):
    html(ui.page_title())

    col_cv, col_offre = st.columns(2, gap="medium")
    with col_cv:
        with st.container(key="card_cv"):
            html(ui.card_head("▤", "violet", "Le CV", "Formats : PDF, DOCX, TXT, MD"))
            cv, cv_name, cv_bytes = read_input("CV", "cv")
    with col_offre:
        with st.container(key="card_offre"):
            html(ui.card_head("◎", "cyan", "L'offre d'emploi", "Analyse l'adéquation réelle"))
            offre, offre_name, _ = read_input("Offre", "offre")
            if st.session_state.get("offer_imported") and not offre_name:
                html(ui.imported_tag())

    # -----------------------------------------------------------------------
    # Vue 1 : analyse + lettre
    # -----------------------------------------------------------------------
    if nav == NAV[0]:
        with st.container(key="card_settings"):
            s1, s2 = st.columns([3, 1.4])
            with s1:
                html(ui.card_head("⚙", "solid", "Réglages de la lettre & paramètres d'évaluation RH",
                                  sub="Configurez la tonalité de la lettre et l'angle d'évaluation de l'agent."))
            with s2:
                with st.container(key="run"):
                    run = st.button("▶ Lancer l'analyse complète", type="primary", use_container_width=True)
            c1, c2, c3 = st.columns(3)
            ton = c1.selectbox("Ton de la lettre", ["professionnel et chaleureux", "formel et sobre", "dynamique et motivé", "créatif et personnel"])
            mots = c2.slider("Longueur de la lettre (mots)", 150, 500, 300, step=50)
            focus_label = c3.selectbox("Priorité d'évaluation", list(FOCUS))
            c4, c5 = st.columns([1, 2])
            langue = c4.selectbox("Langue", LANGS)
            consigne = c5.text_input("Consigne supplémentaire (facultatif)", placeholder="Ex. : insister sur ma reconversion…")
        options = LetterOptions(ton=ton, langue=langue, longueur_mots=mots, consigne=consigne)

        if run:
            t0 = time.perf_counter()
            try:
                with st.status("L'agent travaille…", expanded=True) as status:
                    st.write("Lecture et comparaison du CV et de l'offre…")
                    new_analysis = agent.analyze(cv, offre, FOCUS[focus_label])
                    # l'analyse est conservée même si la rédaction de la lettre échoue ensuite
                    st.session_state.update(
                        analysis=new_analysis, letter="", letter_edit="", letter_err="",
                        elapsed=time.perf_counter() - t0, source=cv_name or "CV collé",
                    )
                    st.write("Rédaction de la lettre…")
                    placeholder, buf = st.empty(), []

                    def on_delta(d: str) -> None:
                        buf.append(d)
                        placeholder.markdown("".join(buf))

                    try:
                        letter = agent.write_letter(cv, offre, new_analysis, options, on_delta=on_delta)
                        st.session_state.update(letter=letter, letter_edit=letter)
                        status.update(label="Terminé", state="complete")
                    except LLMError as exc:
                        st.session_state["letter_err"] = str(exc)
                        status.update(label="Analyse terminée, lettre à relancer", state="error")
                st.rerun()
            except (InputError, LLMError) as exc:
                st.error(str(exc))

        if analysis:
            html(ui.dash_header(st.session_state.get("elapsed"), st.session_state.get("source", "")))
            html(ui.kpi_row(analysis))
            html(ui.skills_matrix(analysis))

            t_letter, t_plan = st.tabs(["Lettre de motivation sur-mesure", "Plan d'amélioration du CV"])
            with t_letter:
                if not current_letter:
                    st.warning(st.session_state.get("letter_err") or "La lettre n'a pas encore été rédigée.")
                    if st.button("✍ Rédiger la lettre", type="primary", key="btn_letter"):
                        try:
                            with st.spinner("Rédaction de la lettre…"):
                                letter = agent.write_letter(cv, offre, analysis, options)
                            st.session_state.update(letter=letter, letter_edit=letter, letter_err="")
                            st.rerun()
                        except (InputError, LLMError) as exc:
                            st.session_state["letter_err"] = str(exc)
                            st.error(str(exc))
                else:
                    html(ui.letter_bar(analysis.poste, analysis.entreprise))
                    html(ui.letter_doc(current_letter, analysis.mots_cles.presents))
                    d1, d2, d3 = st.columns([1, 1, 2])
                    d1.download_button("⬇ Télécharger (.docx)", letter_docx_bytes(current_letter), "lettre-de-motivation.docx", DOCX, use_container_width=True)
                    d2.download_button("⬇ Texte (.txt)", current_letter, "lettre-de-motivation.txt", use_container_width=True)
                    with st.expander("Modifier le texte ou demander une révision"):
                        st.text_area("Lettre (modifiable)", height=320, key="letter_edit")
                        st.text_input("Demander une révision", placeholder="« plus court », « ajoute mon bénévolat »…", key="rev_text")
                        st.button("Réécrire", on_click=rewrite_letter, args=(agent, cv, offre, analysis, options))
                        if st.session_state.get("rev_error"):
                            st.error(st.session_state.pop("rev_error"))

            with t_plan:
                a1, a2 = st.columns(2)
                with a1:
                    st.markdown("#### Points forts")
                    for s in analysis.points_forts:
                        st.markdown(f"- **{s.titre}** — {s.preuve}")
                with a2:
                    st.markdown("#### Écarts et conseils")
                    for g in analysis.ecarts:
                        st.markdown(f"- **{g.titre}** — {g.detail}  \n  ➜ _{g.conseil}_")
                    if not analysis.ecarts:
                        st.write("Aucun écart majeur.")
                st.markdown("#### Pour améliorer le CV")
                for c in analysis.conseils_cv:
                    st.markdown(f"- {c}")
                st.markdown("#### Résumé")
                st.write(analysis.resume)
                r1, r2 = st.columns(2)
                r1.download_button("Rapport (.md)", report_markdown(analysis), "rapport.md", "text/markdown", use_container_width=True)
                r2.download_button("Rapport (.docx)", report_docx_bytes(analysis), "rapport.docx", DOCX, use_container_width=True)

    # -----------------------------------------------------------------------
    # Vue 2 : recherche d'offres
    # -----------------------------------------------------------------------
    elif nav == NAV[1]:
        with st.container(key="card_jobs"):
            html(ui.card_head("🔎", "violet", "Chercher des offres adaptées à votre CV",
                              sub="Sources gratuites : Remotive et Arbeitnow (télétravail, Europe). Pour la Tunisie, utilisez les liens LinkedIn / Indeed."))
            q_text = st.text_input("Mots-clés (séparés par des virgules ; vide = déduits de votre CV)", key="q_text")
            lieu = st.text_input("Lieu pour les liens de recherche manuelle", value="Tunisia", key="lieu")
            with st.container(key="run"):
                go = st.button("▶ Chercher des offres", type="primary", key="btn_jobs")
            if go:

                def do_search():
                    queries = [q.strip() for q in q_text.split(",") if q.strip()] or agent.suggest_queries(cv)
                    with st.spinner("Recherche des offres…"):
                        offers, errors = search_jobs(queries)
                    ranked = []
                    if offers:
                        with st.spinner("Classement selon votre CV…"):
                            ranked = agent.rank_offers(cv, offers, top=10)
                    st.session_state["jobs"] = {"queries": queries, "errors": errors, "ranked": ranked}
                    return True

                guard(do_search)

        res = st.session_state.get("jobs")
        if res:
            st.write("Requêtes : " + ", ".join(res["queries"]))
            for err in res["errors"]:
                st.warning(f"Source indisponible : {err}")
            links = manual_search_links(res["queries"][0], st.session_state.get("lieu", ""))
            st.markdown("Recherche manuelle : " + " · ".join(f"[{n}]({u})" for n, u in links.items()))
            if not res["ranked"]:
                st.info("Aucune offre trouvée par les sources automatiques.")
            for job, m in res["ranked"]:
                with st.expander(f"{m.score}%  ·  {job.titre} — {job.entreprise}  ({job.lieu})"):
                    st.write(m.raison)
                    st.caption(f"{job.source} · {job.date}")
                    if job.url:
                        st.markdown(f"[Voir l'offre]({job.url})")
                    st.write(job.description[:1200] + ("…" if len(job.description) > 1200 else ""))
                    st.button("Utiliser cette offre", key=f"use_{job.id}", on_click=use_offer, args=(job.as_text(),),
                              help="Place l'offre dans la carte ci-dessus et revient à l'analyse.")

    # -----------------------------------------------------------------------
    # Vue 3 : entretien
    # -----------------------------------------------------------------------
    elif nav == NAV[2]:
        with st.container(key="card_itw"):
            html(ui.card_head("🎤", "violet", "Préparer l'entretien",
                              sub="Questions probables, pistes de réponse tirées de votre CV, et entraînement noté."))
            with st.container(key="run"):
                go = st.button("▶ Générer les questions", type="primary", key="btn_itw")
            if go:

                def do_prep():
                    with st.spinner("Préparation…"):
                        st.session_state["prep"] = agent.prepare_interview(cv, offre, analysis)
                    st.session_state.pop("fb", None)
                    return True

                if guard(do_prep):
                    st.rerun()

        prep = st.session_state.get("prep")
        if prep:
            for i, q in enumerate(prep.questions, 1):
                with st.expander(f"{i}. [{q.categorie}] {q.question}"):
                    st.markdown(f"**Ce que le recruteur évalue :** {q.objectif}")
                    st.markdown(f"**Piste de réponse :** {q.piste_reponse}")
            st.markdown("#### Questions à poser au recruteur")
            for x in prep.questions_a_poser:
                st.markdown(f"- {x}")
            st.markdown("#### Conseils")
            for x in prep.conseils:
                st.markdown(f"- {x}")
            d1, d2 = st.columns(2)
            d1.download_button("Fiche (.md)", interview_markdown(prep), "entretien.md", "text/markdown", use_container_width=True)
            d2.download_button("Fiche (.docx)", interview_docx_bytes(prep), "entretien.docx", DOCX, use_container_width=True)

            with st.container(key="card_train"):
                html(ui.card_head("✎", "cyan", "S'entraîner", sub="Répondez à une question, l'agent note et propose une version améliorée."))
                labels = [f"{i}. {q.question}" for i, q in enumerate(prep.questions, 1)]
                choice = st.selectbox("Question", labels)
                question = prep.questions[labels.index(choice)]
                answer = st.text_area("Votre réponse", height=150, key="itw_answer")
                if st.button("Évaluer ma réponse", key="btn_fb", type="primary"):

                    def do_fb():
                        with st.spinner("Évaluation…"):
                            st.session_state["fb"] = agent.evaluate_answer(cv, offre, question, answer)
                        return True

                    guard(do_fb)
                fb = st.session_state.get("fb")
                if fb:
                    st.metric("Note", f"{fb.note}/10")
                    f1, f2 = st.columns(2)
                    with f1:
                        st.markdown("**Points forts**")
                        for x in fb.points_forts:
                            st.markdown(f"- {x}")
                    with f2:
                        st.markdown("**À améliorer**")
                        for x in fb.a_ameliorer:
                            st.markdown(f"- {x}")
                    st.markdown("**Version améliorée**")
                    st.info(fb.version_amelioree)

    # -----------------------------------------------------------------------
    # Vue 4 : e-mail
    # -----------------------------------------------------------------------
    else:
        with st.container(key="card_mail"):
            html(ui.card_head("✉", "violet", "E-mail de candidature",
                              sub="Rien n'est jamais envoyé sans votre relecture et votre confirmation explicite."))
            m1, m2, m3 = st.columns(3)
            to = m1.text_input("Adresse du destinataire", placeholder="recrutement@entreprise.com")
            entreprise = m2.text_input("Entreprise", value=analysis.entreprise if analysis else "")
            poste = m3.text_input("Poste visé", value=analysis.poste if analysis else "")
            mail_lang = st.selectbox("Langue de l'e-mail", LANGS, key="mail_lang")
            has_letter = bool(current_letter)
            attach_letter = st.checkbox("Joindre la lettre de motivation (.docx)", value=has_letter, disabled=not has_letter)
            attach_cv = st.checkbox("Joindre le CV importé", value=bool(cv_bytes), disabled=not cv_bytes)
            with st.container(key="run"):
                go = st.button("▶ Générer le brouillon", type="primary", key="btn_mail")
            if go:

                def do_draft():
                    with st.spinner("Rédaction…"):
                        d = agent.draft_email(cv, entreprise=entreprise, poste=poste, langue=mail_lang,
                                              offre=offre or None, joint_lettre=attach_letter)
                    st.session_state["mail_subject"], st.session_state["mail_body"] = " ".join(d.objet.split()), d.corps
                    return True

                guard(do_draft)

        if "mail_body" in st.session_state:
            with st.container(key="card_mail2"):
                subject = st.text_input("Objet", key="mail_subject")
                body = st.text_area("Message (modifiable)", height=260, key="mail_body")
                attachments = []
                if attach_cv and cv_bytes:
                    attachments.append((cv_name or "CV.pdf", cv_bytes))
                if attach_letter:
                    attachments.append(("lettre-de-motivation.docx", letter_docx_bytes(current_letter)))
                st.caption("Pièces jointes : " + (", ".join(n for n, _ in attachments) or "aucune"))
                try:
                    preview = build_message(to or "destinataire@exemple.com", subject, body, attachments)
                    st.download_button("Télécharger le brouillon (.eml)", to_eml(preview), "candidature.eml", "message/rfc822")
                except MailError as exc:
                    st.error(str(exc))

                try:
                    smtp = SmtpSettings.from_env()
                except ConfigError as exc:
                    smtp = None
                    st.info(f"{exc} En attendant, téléchargez le brouillon (.eml) et envoyez-le depuis votre messagerie.")

                sent = st.session_state.get("sent_count", 0)
                if smtp:
                    confirmed = st.checkbox(f"J'ai relu l'e-mail et je confirme l'envoi à **{to or '…'}**", key="confirm_send")
                    if st.button("Envoyer", disabled=not (confirmed and to), key="btn_send"):
                        if sent >= MAX_SENDS_PER_SESSION:
                            st.error(f"Limite de {MAX_SENDS_PER_SESSION} envois par session atteinte (anti-spam).")
                        else:

                            def do_send():
                                send(smtp, build_message(to, subject, body, attachments, sender=smtp.sender))
                                st.session_state["sent_count"] = sent + 1
                                st.success(f"E-mail envoyé à {to}.")
                                return True

                            guard(do_send)
                    st.caption(f"Envois cette session : {sent}/{MAX_SENDS_PER_SESSION}")

html(ui.footer(settings.provider, settings.model))
