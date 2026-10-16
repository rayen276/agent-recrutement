"""Composants visuels de l'interface web (HTML/CSS pur, sans dépendance à Streamlit).

Toutes les valeurs dynamiques sont échappées : les textes venant du CV, d'une offre ou du modèle
ne peuvent pas injecter de HTML.
"""

from __future__ import annotations

import html
import re

from .models import Analysis


def esc(x: object) -> str:
    return html.escape(str(x), quote=True)


def _flat(s: str) -> str:
    """Supprime les retours à la ligne et l'indentation : Markdown ne doit pas y voir un bloc de code."""
    return re.sub(r">\s+<", "><", " ".join(s.split()))


CSS = _flat("") + """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--violet:#7c3aed;--violet-2:#6d28d9;--violet-soft:#f3edff;--cyan:#0891b2;--cyan-soft:#e6f8fb;
--green:#10b981;--green-soft:#ecfdf5;--amber:#f59e0b;--amber-soft:#fffbeb;--ink:#0f172a;--muted:#64748b;
--line:#eceff4;--bg:#f8fafc;}
.stApp{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--ink);}
.stApp input,.stApp textarea,.stApp button,.stApp select{font-family:inherit;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg) !important;}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],
[data-testid="stDecoration"],#MainMenu,footer{display:none !important;}
[data-testid="stMainBlockContainer"]{max-width:100% !important;width:100%;margin:0 !important;padding:0 !important;background:var(--bg);}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]{gap:0 !important;}

/* ---- en-tête ---- */
.st-key-hdr{background:#fff;border-bottom:1px solid var(--line);padding:14px max(24px,calc((100vw - 1280px)/2));}
.st-key-hdr [data-testid="stHorizontalBlock"]{align-items:center;gap:12px;}
.brand{display:flex;align-items:center;gap:11px;}
.logo{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,#8b5cf6,#4f46e5);color:#fff;
display:grid;place-items:center;font-size:18px;box-shadow:0 4px 12px rgba(99,70,229,.35);flex:none;}
.brand-t{font-weight:800;font-size:15px;letter-spacing:-.01em;white-space:nowrap;}
.brand-t em{font-style:normal;font-weight:500;color:var(--violet);margin-left:4px;}
.badge{display:inline-block;margin-left:8px;font-size:9.5px;font-weight:700;color:var(--violet);background:var(--violet-soft);
padding:2px 7px;border-radius:999px;letter-spacing:.04em;vertical-align:1px;}
.brand-s{font-size:10.5px;color:var(--muted);margin-top:1px;}
.pill-ok{display:inline-flex;align-items:center;gap:7px;font-size:11.5px;font-weight:600;color:#047857;background:var(--green-soft);
border:1px solid #bbf7d0;padding:7px 13px;border-radius:999px;white-space:nowrap;}
.pill-ok i{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;box-shadow:0 0 0 3px rgba(16,185,129,.18);}
.st-key-navbox [data-testid="stRadio"] > div{gap:4px;}
.st-key-navbox [role="radiogroup"]{gap:4px;flex-wrap:nowrap;}
.st-key-navbox [role="radiogroup"] label{padding:8px 13px;border-radius:10px;cursor:pointer;margin:0;background:transparent;}
.st-key-navbox [data-testid="stRadioOption"] > div > div:first-child{display:none;}
.st-key-navbox [role="radiogroup"] label p{font-size:12.5px;font-weight:600;color:var(--muted);white-space:nowrap;}
.st-key-navbox [role="radiogroup"] label:hover{background:#f1f5f9;}
.st-key-navbox [data-testid="stRadioOption"][data-selected="true"]{background:var(--violet-soft);}
.st-key-navbox [data-testid="stRadioOption"][data-selected="true"] p{color:var(--violet-2);}

/* ---- contenu ---- */
.st-key-content{max-width:1280px;width:100%;margin:0 auto;padding:26px 24px 40px;}
.st-key-content [data-testid="stVerticalBlock"]{gap:1rem;}
.page-title{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:800;letter-spacing:-.02em;margin:0;}
.page-title .ico{width:38px;height:38px;border-radius:10px;background:var(--violet-soft);color:var(--violet);display:grid;place-items:center;font-size:18px;}
.page-sub{color:var(--muted);font-size:13.5px;margin:6px 0 0;max-width:640px;line-height:1.55;}
.hr{height:1px;background:var(--line);margin:18px 0 4px;}
[class*="st-key-card_"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.card-h{display:flex;align-items:center;gap:9px;margin-bottom:4px;}
.ic{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:12px;flex:none;}
.ic-violet{background:var(--violet-soft);color:var(--violet);}
.ic-cyan{background:var(--cyan-soft);color:var(--cyan);}
.ic-solid{background:var(--violet);color:#fff;}
.card-t{font-weight:700;font-size:14.5px;}
.card-hint{margin-left:auto;font-size:10.5px;color:var(--muted);}
.card-sub{font-size:11.5px;color:var(--muted);margin:2px 0 10px 33px;}
.st-key-content h3,.st-key-content h4{font-size:15px !important;font-weight:700 !important;letter-spacing:-.01em;margin-top:6px;}
.lbl{font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin:8px 0 6px;}
.tag{display:inline-block;font-size:10.5px;font-weight:600;padding:3px 9px;border-radius:7px;}
.tag-cyan{background:var(--cyan-soft);color:var(--cyan);}

/* ---- champs ---- */
[data-testid="stFileUploaderDropzone"]{background:var(--bg);border:1px dashed #cbd5e1;border-radius:10px;padding:10px 12px;}
[data-testid="stFileUploaderDropzone"] small{font-size:10.5px;}
[data-testid="stFileUploaderDropzone"] button{border-radius:8px;font-size:12px;}
[data-testid="stTextArea"] textarea{font-family:'JetBrains Mono',ui-monospace,monospace !important;font-size:11.5px !important;
background:var(--bg) !important;line-height:1.55;}
[data-baseweb="textarea"],[data-baseweb="base-input"],[data-baseweb="select"] > div{background:var(--bg) !important;border-color:#e5e7eb !important;border-radius:10px !important;}
[data-testid="stWidgetLabel"] p{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);}
.stApp .stButton button,.stApp .stDownloadButton button{border-radius:10px;font-weight:600;font-size:12.5px;border:1px solid #e2e8f0;background:#fff;color:var(--ink);}
.stApp .stButton button:hover,.stApp .stDownloadButton button:hover{border-color:var(--violet);color:var(--violet-2);}
.stApp button[data-testid="stBaseButton-primary"],.stApp .stButton button[data-testid="stBaseButton-primary"],
.stApp .stDownloadButton button[data-testid="stBaseButton-primary"]{background:linear-gradient(90deg,#7c3aed,#4f46e5);
color:#fff;border:none;box-shadow:0 6px 16px rgba(99,70,229,.3);}
.stApp button[data-testid="stBaseButton-primary"] p{color:#fff;}
.stApp button[data-testid="stBaseButton-primary"]:hover{filter:brightness(1.07);color:#fff;}
.stApp button[data-testid="stBaseButton-primary"]:disabled{opacity:.45;box-shadow:none;filter:none;}
.st-key-run button[data-testid="stBaseButton-primary"]{background:linear-gradient(90deg,#7c3aed,#0891b2);}
[data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line);}
[data-baseweb="tab"]{font-size:12.5px;font-weight:600;color:var(--muted);}
[aria-selected="true"][data-baseweb="tab"]{color:var(--violet-2);}
[data-baseweb="tab-highlight"]{background:var(--violet) !important;}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:12px;background:#fff;}
[data-testid="stSlider"] [role="slider"]{background:var(--violet);}

/* ---- tableau de bord ---- */
.dash-h{display:flex;align-items:center;gap:10px;margin:8px 0 2px;}
.dash-t{font-size:19px;font-weight:800;letter-spacing:-.015em;}
.dash-t i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);margin-left:8px;vertical-align:middle;}
.chip-time{margin-left:auto;font-size:11px;color:var(--muted);background:#fff;border:1px solid var(--line);padding:7px 12px;border-radius:9px;}
.dash-s{font-size:11.5px;color:var(--muted);margin:0 0 12px;}
.kpis{display:grid;grid-template-columns:1.05fr 1fr 1fr 1fr;gap:14px;}
@media(max-width:860px){.kpis{grid-template-columns:1fr 1fr;}}
.kpi{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;min-height:190px;}
.kpi-score{background:linear-gradient(135deg,#faf7ff,#fff 60%);align-items:center;text-align:center;}
.kpi-l{font-size:10px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:var(--violet);}
.ring{width:104px;height:104px;border-radius:50%;margin:12px auto 10px;display:grid;place-items:center;}
.ring-in{width:80px;height:80px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:25px;font-weight:800;letter-spacing:-.02em;}
.ring-in small{font-size:12px;font-weight:700;color:var(--muted);margin:5px 0 0 1px;}
.kpi-cap{font-size:11px;color:var(--muted);line-height:1.4;}
.kpi-top{display:flex;align-items:center;justify-content:space-between;font-size:11.5px;font-weight:700;margin-bottom:9px;}
.kpi-top span:last-child{font-size:11px;}
.bar{height:5px;border-radius:99px;background:#eef2f6;overflow:hidden;}
.bar b{display:block;height:100%;border-radius:99px;}
.kpi-d{margin-top:auto;padding-top:12px;border-top:1px solid var(--line);font-size:11px;color:var(--muted);line-height:1.5;}
.c-cyan{color:var(--cyan);}.c-amber{color:#d97706;}.c-violet{color:var(--violet);}
.bg-cyan{background:var(--cyan);}.bg-amber{background:var(--amber);}.bg-violet{background:var(--violet);}

/* ---- matrice ---- */
.mx{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:14px;}
.mx-h{display:flex;align-items:center;margin-bottom:12px;}
.mx-h b{font-size:14px;}
.mx-h span{margin-left:auto;font-size:10.5px;color:var(--muted);}
.mx-g{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}
@media(max-width:860px){.mx-g{grid-template-columns:1fr;}}
.mx-c{border-radius:12px;padding:13px 14px;border:1px solid;}
.mx-ok{background:var(--green-soft);border-color:#bbf7d0;}
.mx-mid{background:var(--amber-soft);border-color:#fde68a;}
.mx-no{background:#f8fafc;border-color:#e2e8f0;}
.mx-t{font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;margin-bottom:9px;}
.mx-ok .mx-t{color:#047857;}.mx-mid .mx-t{color:#b45309;}.mx-no .mx-t{color:#475569;}
.sk{display:inline-block;font-size:11px;background:#fff;border:1px solid rgba(15,23,42,.1);border-radius:7px;padding:3px 9px;margin:0 6px 6px 0;line-height:1.35;}
.mx-empty{font-size:11px;color:var(--muted);}

/* ---- lettre ---- */
.letter-bar{display:flex;align-items:center;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:10px 14px;font-size:11.5px;color:var(--muted);margin:10px 0 12px;}
.letter-bar b{color:var(--ink);}
.letter-bar b.cy{color:var(--cyan);}
.doc{background:#fff;border:1px solid var(--line);border-radius:12px;padding:30px 34px;box-shadow:0 1px 3px rgba(15,23,42,.05);}
.doc .obj{font-weight:700;font-size:14px;margin:0 0 16px;}
.doc p{font-size:13px;line-height:1.75;color:#334155;margin:0 0 13px;}
.doc mark{border-radius:5px;padding:1px 6px;font-weight:600;}
.doc mark.m1{background:#ede9fe;color:#5b21b6;}
.doc mark.m2{background:#cffafe;color:#0e7490;}
.doc .sig{font-weight:700;color:var(--ink);}

/* ---- pied ---- */
.ftr{display:flex;align-items:center;gap:14px;background:#fff;border-top:1px solid var(--line);padding:14px max(24px,calc((100vw - 1280px)/2));font-size:11px;color:var(--muted);}
.ftr b{color:var(--ink);}
.ftr .r{margin-left:auto;display:flex;align-items:center;gap:7px;color:#047857;font-weight:600;}
.ftr .r i{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;}
</style>"""


# --------------------------------------------------------------------------
# Briques HTML
# --------------------------------------------------------------------------
def brand() -> str:
    return _flat(
        '<div class="brand"><div class="logo">✦</div><div>'
        '<div class="brand-t">Agent RH<em>intelligence</em><span class="badge">v1.0</span></div>'
        '<div class="brand-s">Analyse CV/offre · Lettre · Entretien</div></div></div>'
    )


def status_pill(model: str) -> str:
    return f'<span class="pill-ok" title="{esc(model)}"><i></i>IA connectée</span>'


def page_title() -> str:
    return _flat(
        '<div class="page-title"><span class="ico">✉</span>Agent RH : CV, offre et lettre de motivation</div>'
        '<p class="page-sub">Analyse la correspondance entre un CV et une offre, puis rédige une lettre sur mesure '
        "et prépare vos entretiens.</p><div class=\"hr\"></div>"
    )


def card_head(icon: str, color: str, title: str, hint: str = "", sub: str = "") -> str:
    return _flat(
        f'<div class="card-h"><span class="ic ic-{esc(color)}">{esc(icon)}</span><span class="card-t">{esc(title)}</span>'
        f'<span class="card-hint">{esc(hint)}</span></div>' + (f'<div class="card-sub">{esc(sub)}</div>' if sub else "")
    )


def label(text: str) -> str:
    return f'<div class="lbl">{esc(text)}</div>'


def imported_tag() -> str:
    return '<span class="tag tag-cyan">Texte importé</span>'


def dash_header(elapsed: float | None, source: str) -> str:
    chip = f'<span class="chip-time">Temps de traitement : {elapsed:.1f} s</span>' if elapsed else ""
    sub = f"Rapport basé sur l'analyse sémantique du document {esc(source)} face à l'offre." if source else ""
    return _flat(
        f'<div class="dash-h"><span class="dash-t">Tableau de bord : Correspondance &amp; Diagnostic IA<i></i></span>{chip}</div>'
        f'<div class="dash-s">{sub}</div>'
    )


# --------------------------------------------------------------------------
# Indicateurs calculés à partir de l'analyse (aucune valeur inventée)
# --------------------------------------------------------------------------
def _pct(part: float, whole: float) -> int:
    """Pourcentage arrondi à l'entier le plus proche (0,5 vers le haut, contrairement à round())."""
    return int(100 * part / whole + 0.5)


def compute_metrics(a: Analysis) -> dict:
    reqs = a.exigences
    total = len(reqs) or 1
    covered = [r for r in reqs if r.statut == "couvert"]
    partial = [r for r in reqs if r.statut == "partiel"]
    absent = [r for r in reqs if r.statut == "absent"]
    req_pct = _pct(len(covered) + 0.5 * len(partial), total)
    kw_total = len(a.mots_cles.presents) + len(a.mots_cles.manquants)
    kw_pct = _pct(len(a.mots_cles.presents), kw_total) if kw_total else None
    to_fix_pct = _pct(len(partial) + len(absent), total)
    return {
        "req_pct": req_pct,
        "kw_pct": kw_pct,
        "to_fix_pct": to_fix_pct,
        "covered": covered,
        "partial": partial,
        "absent": absent,
    }


def _verdict(score: int) -> tuple[str, str]:
    if score >= 75:
        return "#10b981", "Candidature très compatible avec l'offre."
    if score >= 50:
        return "#f59e0b", "Compatibilité correcte, à renforcer sur quelques points."
    return "#ef4444", "Compatibilité limitée : travaillez les écarts avant de postuler."


def _short(items: list[str], n: int = 2, empty: str = "—") -> str:
    items = [i for i in items if i]
    return esc(", ".join(i[:48] for i in items[:n])) if items else empty


def kpi_row(a: Analysis) -> str:
    m = compute_metrics(a)
    color, verdict = _verdict(a.score)
    score = _flat(
        f'<div class="kpi kpi-score"><div class="kpi-l">Score global IA</div>'
        f'<div class="ring" style="background:conic-gradient({color} {a.score}%,#e5e7eb 0)"><div class="ring-in">{a.score}<small>%</small></div></div>'
        f'<div class="kpi-cap">{esc(verdict)}</div></div>'
    )

    def metric(title, value, pct, cls, desc):
        w = 0 if pct is None else max(0, min(100, pct))
        return _flat(
            f'<div class="kpi"><div class="kpi-top"><span>{esc(title)}</span><span class="c-{cls}">{esc(value)}</span></div>'
            f'<div class="bar"><b class="bg-{cls}" style="width:{w}%"></b></div><div class="kpi-d">{desc}</div></div>'
        )

    cards = [
        metric("Exigences couvertes", f"{m['req_pct']}%", m["req_pct"], "cyan",
               "Couvert : " + _short([r.exigence for r in m["covered"]])),
        metric("Mots-clés de l'offre", "—" if m["kw_pct"] is None else f"{m['kw_pct']}%", m["kw_pct"], "amber",
               "Manquants : " + _short(a.mots_cles.manquants, 3)),
        metric("Exigences à renforcer", f"{m['to_fix_pct']}%", m["to_fix_pct"], "violet",
               "À traiter : " + _short([g.titre for g in a.ecarts] or [r.exigence for r in m["absent"] + m["partial"]])),
    ]
    return f'<div class="kpis">{score}{"".join(cards)}</div>'


def skills_matrix(a: Analysis) -> str:
    m = compute_metrics(a)

    def chips(items: list[str]) -> str:
        items = list(dict.fromkeys(i.strip() for i in items if i and i.strip()))[:10]
        return "".join(f'<span class="sk">{esc(i[:44])}</span>' for i in items) or '<span class="mx-empty">Aucun élément.</span>'

    ok = [r.exigence for r in m["covered"]] + [s.titre for s in a.points_forts]
    mid = [r.exigence for r in m["partial"]]
    no = [r.exigence for r in m["absent"]] + list(a.mots_cles.manquants)
    return _flat(
        '<div class="mx"><div class="mx-h"><b>Matrice des compétences requises vs profil</b>'
        "<span>Relevé automatique des exigences de l'offre</span></div><div class=\"mx-g\">"
        f'<div class="mx-c mx-ok"><div class="mx-t">✓ Acquis &amp; prêts (points forts)</div>{chips(ok)}</div>'
        f'<div class="mx-c mx-mid"><div class="mx-t">⚠ À consolider / partiel</div>{chips(mid)}</div>'
        f'<div class="mx-c mx-no"><div class="mx-t">○ Non mentionné / à vérifier</div>{chips(no)}</div>'
        "</div></div>"
    )


def letter_bar(poste: str, entreprise: str) -> str:
    who = f"<b>{esc(poste)}</b>" if poste else "<b>ce poste</b>"
    if entreprise:
        who += f' chez <b class="cy">{esc(entreprise)}</b>'
    return f'<div class="letter-bar"><span>Rédigée sur mesure pour {who}</span></div>'


def letter_doc(letter: str, keywords: list[str] | None = None) -> str:
    """Rend la lettre comme un document ; met en évidence les mots-clés de l'offre."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", letter.strip()) if p.strip()]
    kws = sorted({k.strip() for k in (keywords or []) if k and len(k.strip()) >= 3}, key=len, reverse=True)
    pattern = re.compile("(" + "|".join(re.escape(esc(k)) for k in kws) + ")", re.IGNORECASE) if kws else None
    classes: dict[str, str] = {}

    def mark(match: re.Match) -> str:
        word = match.group(0)
        cls = classes.setdefault(word.lower(), "m1" if len(classes) % 2 == 0 else "m2")
        return f'<mark class="{cls}">{word}</mark>'

    out = []
    for i, p in enumerate(paras):
        safe = esc(p).replace("\n", "<br>")
        if pattern:
            safe = pattern.sub(mark, safe)
        if i == 0 and p.lower().startswith("objet"):
            out.append(f'<p class="obj">{safe}</p>')
        elif i == len(paras) - 1 and len(p) < 80:
            out.append(f'<p class="sig">{safe}</p>')
        else:
            out.append(f"<p>{safe}</p>")
    return f'<div class="doc">{"".join(out)}</div>'


def footer(provider: str, model: str) -> str:
    return _flat(
        '<div class="ftr"><span>✦ <b>Agent RH</b> · Vos documents restent sur votre machine ; seuls les textes analysés '
        "sont envoyés au fournisseur d'IA.</span>"
        f'<span class="r"><i></i>{esc(provider)} · {esc(model)} (opérationnel)</span></div>'
    )
