import os
import json
import html
import hashlib
from io import BytesIO
from datetime import date

import streamlit as st
from google import genai

try:
    from pypdf import PdfReader          # maintained successor to PyPDF2
except ImportError:                       # pragma: no cover
    from PyPDF2 import PdfReader

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)


# =========================================================
# CONFIG
# =========================================================

MODEL = "gemini-3.5-flash-lite"

PAGES = [
    ("overview",    "Overview",     "Score and profile"),
    ("skills",      "Skills",       "What your resume proves"),
    ("experience",  "Experience",   "History and role fit"),
    ("suggestions", "Improvements", "What to change next"),
]

st.set_page_config(
    page_title="Resume AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DESIGN SYSTEM
# =========================================================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');

:root {
    --ink:       #14142B;
    --ink-soft:  #4A4B63;
    --muted:     #7B7C92;
    --line:      #E4E6EF;
    --canvas:    #F4F5F9;
    --surface:   #FFFFFF;
    --indigo:    #3D2E8F;
    --indigo-dk: #1B1A4A;
    --good:      #1F9254;
    --warn:      #B7791F;
    --bad:       #C23B3B;
}

html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }

.stApp { background: var(--canvas); }
#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 1.25rem 2.25rem 3rem;
    max-width: 1320px;
}

/* ---------------- sidebar ---------------- */

section[data-testid="stSidebar"] {
    background: var(--indigo-dk);
    border-right: none;
}
section[data-testid="stSidebar"] * { color: #EDEDF5; }

section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 19px;
    font-weight: 700;
    letter-spacing: -0.01em;
    padding: 4px 6px 18px;
}
.brand-mark {
    width: 30px; height: 30px;
    border-radius: 8px;
    background: linear-gradient(135deg, #6F5CE0, #3D2E8F);
    display: grid; place-items: center;
    font-size: 15px;
}

.nav-label {
    font-size: 11px;
    font-weight: 600;
    color: #8382B8 !important;
    padding: 14px 8px 6px;
}

/* sidebar nav buttons */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #B9B8D8;
    font-size: 14px;
    font-weight: 500;
    text-align: left;
    justify-content: flex-start;
    padding: 9px 12px;
    height: auto;
    transition: background .15s ease, color .15s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.07);
    color: #FFFFFF;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(255,255,255,.12);
    color: #FFFFFF;
    font-weight: 600;
    box-shadow: inset 3px 0 0 #8B7BF0;
}

.side-meta {
    margin-top: 22px;
    padding: 12px;
    border-radius: 10px;
    background: rgba(255,255,255,.06);
    font-size: 12px;
    line-height: 1.55;
}
.side-meta .fname {
    font-weight: 600;
    word-break: break-all;
    display: block;
    margin-bottom: 2px;
}
.side-meta .sub { color: #A3A2CC !important; }

/* ---------------- top bar ---------------- */

.topbar {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    padding-bottom: 14px;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--line);
}
.topbar h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--ink);
    margin: 0 0 3px;
}
.topbar p { font-size: 14.5px; color: var(--muted); margin: 0; }

.chip {
    font-size: 13.5px;
    font-weight: 600;
    padding: 5px 12px;
    border-radius: 999px;
    white-space: nowrap;
}
.chip-good { background: #E7F4ED; color: var(--good); }
.chip-warn { background: #FBF2E1; color: var(--warn); }
.chip-bad  { background: #FBEAEA; color: var(--bad); }

/* ---------------- grid + cards ---------------- */

.grid { display: grid; gap: 18px; margin-bottom: 18px; }
.g-score   { grid-template-columns: 300px 1fr; }
.g-2       { grid-template-columns: 1fr 1fr; }
.g-3       { grid-template-columns: repeat(3, 1fr); }
.g-lead    { grid-template-columns: 1.35fr 1fr; }

@media (max-width: 900px) {
    .grid { grid-template-columns: 1fr !important; }
}

.card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 20px 22px;
}
.card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 14px;
}
.card-title .count {
    color: var(--muted);
    font-weight: 500;
    margin-left: 5px;
}
.body-text {
    font-size: 15px;
    line-height: 1.68;
    color: var(--ink-soft);
    max-width: 68ch;
}

/* ---------------- score dial ---------------- */

.dial { display: grid; place-items: center; padding: 6px 0 2px; }
.dial-wrap { position: relative; width: 168px; height: 168px; }
.dial-center {
    position: absolute; inset: 0;
    display: grid; place-content: center; text-align: center;
}
.dial-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 48px;
    font-weight: 700;
    line-height: 1;
    color: var(--ink);
}
.dial-den { font-size: 13px; color: var(--muted); margin-top: 4px; }
.dial-verdict {
    text-align: center;
    font-size: 15.5px;
    font-weight: 600;
    color: var(--ink);
    margin-top: 16px;
}
.dial-note {
    text-align: center;
    font-size: 13.5px;
    color: var(--muted);
    margin-top: 3px;
}

/* ---------------- stat strip ---------------- */

.stat { border-left: 3px solid var(--line); padding-left: 14px; }
.stat-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 27px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.1;
}
.stat-lab { font-size: 13.5px; color: var(--muted); margin-top: 3px; }

/* ---------------- pills + lists ---------------- */

.pills { display: flex; flex-wrap: wrap; gap: 7px; }
.pill {
    font-size: 13.5px;
    font-weight: 500;
    color: #2E4A7A;
    background: #EEF3FB;
    border: 1px solid #DCE6F5;
    border-radius: 7px;
    padding: 5px 11px;
}

.rows { display: flex; flex-direction: column; gap: 11px; }
.row {
    display: flex;
    gap: 10px;
    font-size: 14.5px;
    line-height: 1.6;
    color: var(--ink-soft);
}
.row .dot {
    flex: 0 0 auto;
    width: 6px; height: 6px;
    border-radius: 50%;
    margin-top: 8px;
}
.dot-good { background: var(--good); }
.dot-warn { background: var(--warn); }
.dot-info { background: var(--indigo); }

.step { display: flex; gap: 12px; align-items: flex-start; }
.step-n {
    flex: 0 0 auto;
    width: 22px; height: 22px;
    border-radius: 6px;
    background: #F0EEFA;
    color: var(--indigo);
    font-size: 11.5px;
    font-weight: 700;
    display: grid; place-items: center;
    margin-top: 1px;
}

.role {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 11px 0;
    border-bottom: 1px solid var(--line);
    font-size: 14.5px;
    color: var(--ink);
    font-weight: 500;
}
.role:last-child { border-bottom: none; }
.role .rank { font-size: 12px; color: var(--muted); font-weight: 400; }

/* ---------------- empty state ---------------- */

.empty {
    background: var(--surface);
    border: 1px dashed #D3D6E4;
    border-radius: 12px;
    padding: 46px 30px;
    text-align: center;
}
.empty h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 17px;
    color: var(--ink);
    margin: 0 0 6px;
}
.empty p { font-size: 13.5px; color: var(--muted); margin: 0; }

/* ---------------- main-area widgets ---------------- */

div[data-testid="stFileUploader"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 16px 18px;
}
div[data-testid="stFileUploader"] label { font-size: 13px; font-weight: 600; }

div[data-testid="stMain"] .stButton > button {
    background: var(--indigo);
    color: #fff;
    border: none;
    border-radius: 9px;
    height: 44px;
    font-weight: 600;
    font-size: 15px;
}
div[data-testid="stMain"] .stButton > button:hover { background: #32257A; }
div[data-testid="stMain"] .stButton > button[kind="secondary"] {
    background: var(--surface);
    color: var(--ink-soft);
    border: 1px solid var(--line);
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================

def esc(value):
    """Model output goes into raw HTML, so escape it."""
    return html.escape(str(value))


def tone(score):
    if score >= 80:
        return "good", "#1F9254"
    if score >= 60:
        return "warn", "#B7791F"
    return "bad", "#C23B3B"


def verdict(score):
    if score >= 80:
        return "Strong match", "Most ATS filters will pass this through."
    if score >= 60:
        return "Nearly there", "A few fixes will lift this above the cutoff."
    return "Needs work", "Parsers are likely missing key information."


def card(title, body, count=None):
    tail = f'<span class="count">{count}</span>' if count is not None else ""
    return (
        f'<div class="card"><div class="card-title">{esc(title)}{tail}</div>'
        f'{body}</div>'
    )


def bullet_rows(items, dot="info"):
    if not items:
        return '<div class="body-text">Nothing flagged here.</div>'
    rows = "".join(
        f'<div class="row"><span class="dot dot-{dot}"></span><span>{esc(i)}</span></div>'
        for i in items
    )
    return f'<div class="rows">{rows}</div>'


def numbered_rows(items):
    if not items:
        return '<div class="body-text">Nothing flagged here.</div>'
    rows = "".join(
        f'<div class="step"><span class="step-n">{n}</span>'
        f'<span class="row" style="margin:0">{esc(i)}</span></div>'
        for n, i in enumerate(items, 1)
    )
    return f'<div class="rows">{rows}</div>'


def pills(items):
    if not items:
        return '<div class="body-text">No skills detected.</div>'
    tags = "".join(f'<span class="pill">{esc(i)}</span>' for i in items)
    return f'<div class="pills">{tags}</div>'


def dial(score):
    """SVG ring — the one bold element on the page."""
    radius = 70
    circumference = 2 * 3.14159 * radius
    filled = circumference * min(max(score, 0), 100) / 100
    _, colour = tone(score)
    label, note = verdict(score)

    return f"""
    <div class="dial">
      <div class="dial-wrap">
        <svg width="168" height="168" viewBox="0 0 168 168">
          <circle cx="84" cy="84" r="{radius}" fill="none"
                  stroke="#EDEFF6" stroke-width="13" />
          <circle cx="84" cy="84" r="{radius}" fill="none"
                  stroke="{colour}" stroke-width="13" stroke-linecap="round"
                  stroke-dasharray="{filled:.1f} {circumference:.1f}"
                  transform="rotate(-90 84 84)" />
        </svg>
        <div class="dial-center">
          <div class="dial-num">{score}</div>
          <div class="dial-den">out of 100</div>
        </div>
      </div>
    </div>
    <div class="dial-verdict">{label}</div>
    <div class="dial-note">{note}</div>
    """


def stat(number, label):
    return f'<div class="stat"><div class="stat-num">{number}</div><div class="stat-lab">{esc(label)}</div></div>'


def topbar(title, subtitle, score=None):
    chip = ""
    if score is not None:
        cls, _ = tone(score)
        chip = f'<span class="chip chip-{cls}">ATS score {score}</span>'
    return (
        f'<div class="topbar"><div><h1>{esc(title)}</h1>'
        f'<p>{esc(subtitle)}</p></div>{chip}</div>'
    )


def empty_state(message):
    st.markdown(
        f'<div class="empty"><h3>No analysis yet</h3><p>{esc(message)}</p></div>',
        unsafe_allow_html=True,
    )


def build_report_pdf(filename, score, data):
    """Render the analysis as a one-file PDF report, returned as bytes."""

    ink = HexColor("#14142B")
    ink_soft = HexColor("#4A4B63")
    muted = HexColor("#7B7C92")
    indigo = HexColor("#3D2E8F")
    _, score_hex = tone(score)
    score_colour = HexColor(score_hex)
    line = HexColor("#E4E6EF")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName="Helvetica-Bold",
                         fontSize=22, textColor=ink, alignment=TA_LEFT,
                         spaceAfter=2)
    meta = ParagraphStyle("meta", parent=styles["Normal"], fontName="Helvetica",
                           fontSize=10, textColor=muted, spaceAfter=18)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                         fontSize=12.5, textColor=ink, spaceBefore=16, spaceAfter=8)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica",
                           fontSize=10.5, textColor=ink_soft, leading=15)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, spaceAfter=5,
                             bulletIndent=0)
    score_num = ParagraphStyle("score_num", parent=styles["Normal"],
                                fontName="Helvetica-Bold", fontSize=34,
                                textColor=score_colour, alignment=TA_LEFT)
    score_lab = ParagraphStyle("score_lab", parent=styles["Normal"], fontSize=9.5,
                                textColor=muted)

    story = []

    story.append(Paragraph("Resume Analysis Report", h1))
    story.append(Paragraph(
        f"{esc(filename)} &nbsp;&middot;&nbsp; Generated {date.today():%d %b %Y} "
        f"&nbsp;&middot;&nbsp; Model: {esc(MODEL)}",
        meta,
    ))
    story.append(HRFlowable(width="100%", color=line, thickness=1, spaceAfter=14))

    # Score + profile summary side by side
    verdict_label, verdict_note = verdict(score)
    score_cell = [
        Paragraph(str(score), score_num),
        Paragraph("out of 100", score_lab),
        Spacer(1, 6),
        Paragraph(f"<b>{esc(verdict_label)}</b>", body),
        Paragraph(esc(verdict_note), score_lab),
    ]
    summary_cell = [
        Paragraph("PROFILE SUMMARY", ParagraphStyle(
            "lab", parent=score_lab, fontName="Helvetica-Bold", textColor=indigo)),
        Spacer(1, 4),
        Paragraph(esc(data.get("profile_summary", "Not available.")), body),
    ]
    top_table = Table([[score_cell, summary_cell]], colWidths=[1.6 * inch, 4.7 * inch])
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.75, line),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, line),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("LEFTPADDING", (1, 0), (1, 0), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(top_table)

    def bullet_list(items, marker="•"):
        if not items:
            story.append(Paragraph("Nothing flagged here.", body))
            return
        for item in items:
            story.append(Paragraph(f"{marker} {esc(item)}", bullet))

    story.append(Paragraph("KEY SKILLS", h2))
    skills = data.get("key_skills", [])
    story.append(Paragraph(", ".join(esc(s) for s in skills) or "None detected.", body))

    story.append(Paragraph("EXPERIENCE SUMMARY", h2))
    story.append(Paragraph(esc(data.get("experience_summary", "Not available.")), body))

    story.append(Paragraph("STRENGTHS", h2))
    bullet_list(data.get("strengths", []))

    story.append(Paragraph("AREAS OF IMPROVEMENT", h2))
    bullet_list(data.get("areas_of_improvement", []))

    story.append(Paragraph("RECOMMENDED ROLES", h2))
    bullet_list(data.get("recommended_roles", []))

    story.append(Paragraph("TIPS TO IMPROVE", h2))
    for n, tip in enumerate(data.get("tips_to_improve", []), 1):
        bullet_list([tip], marker=f"{n}.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        title="Resume Analysis Report",
    )
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# BACKEND
# =========================================================

@st.cache_resource
def get_client():
    key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY", "")
    if not key:
        return None
    return genai.Client(api_key=key)


def read_resume(file):
    file.seek(0)
    reader = PdfReader(file)
    return "\n".join(p.extract_text() or "" for p in reader.pages)


PROMPT = """You are an expert ATS resume analyzer.

Analyze the resume below and return ONLY valid JSON with EXACTLY this structure:

{{
    "ats_score": 85,
    "profile_summary": "Short professional summary of the candidate.",
    "key_skills": ["Python", "SQL", "Machine Learning"],
    "experience_summary": "Short summary of the candidate's experience.",
    "strengths": ["Strong technical skills"],
    "areas_of_improvement": ["Add measurable achievements"],
    "recommended_roles": ["Data Scientist"],
    "tips_to_improve": ["Quantify achievements"]
}}

Rules:
- ats_score is an integer between 0 and 100.
- Every other field except the two summaries is a list of short strings.
- Order recommended_roles and tips_to_improve by relevance, strongest first.
- Output JSON only. No markdown fences, no commentary.

Resume:
{resume}
"""


@st.cache_data(show_spinner=False)
def analyze(resume_text, _fingerprint):
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(resume=resume_text),
    )
    raw = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# =========================================================
# STATE + SIDEBAR NAV
# =========================================================

st.session_state.setdefault("page", "analyze")
st.session_state.setdefault("analysis", None)
st.session_state.setdefault("filename", None)

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">📄</span>Resume AI</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "Upload resume",
        use_container_width=True,
        type="primary" if st.session_state.page == "analyze" else "secondary",
    ):
        st.session_state.page = "analyze"
        st.rerun()

    st.markdown('<div class="nav-label">Analysis</div>', unsafe_allow_html=True)

    for key, label, _ in PAGES:
        if st.button(
            label,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if st.session_state.page == key else "secondary",
        ):
            st.session_state.page = key
            st.rerun()

    if st.session_state.analysis:
        st.markdown(
            f'<div class="side-meta"><span class="fname">'
            f'{esc(st.session_state.filename)}</span>'
            f'<span class="sub">Analyzed with {esc(MODEL)}</span></div>',
            unsafe_allow_html=True,
        )


data = st.session_state.analysis or {}
score = int(data.get("ats_score", 0)) if data else None
skills = data.get("key_skills", [])
strengths = data.get("strengths", [])
improvements = data.get("areas_of_improvement", [])
roles = data.get("recommended_roles", [])
tips = data.get("tips_to_improve", [])


# =========================================================
# PAGE — UPLOAD
# =========================================================

if st.session_state.page == "analyze":

    st.markdown(
        topbar(
            "Upload resume",
            "Drop in a PDF and we'll score it the way an applicant tracking system would.",
            score,
        ),
        unsafe_allow_html=True,
    )

    if get_client() is None:
        st.error("Set GOOGLE_API_KEY in your environment or .streamlit/secrets.toml to run an analysis.")
        st.stop()

    left, right = st.columns([1.35, 1], gap="large")

    with left:
        uploaded = st.file_uploader("Resume (PDF)", type=["pdf"])

        if uploaded:
            st.caption(f"Ready: {uploaded.name}")

            if st.button("Analyze resume", use_container_width=True):
                with st.spinner("Reading the PDF and scoring it…"):
                    try:
                        text = read_resume(uploaded)

                        if len(text.strip()) < 80:
                            st.error(
                                "Almost no text came out of this PDF. It's probably a scan "
                                "or an image export — try saving it again as a text PDF."
                            )
                            st.stop()

                        fingerprint = hashlib.md5(text.encode()).hexdigest()
                        st.session_state.analysis = analyze(text, fingerprint)
                        st.session_state.filename = uploaded.name
                        st.session_state.page = "overview"
                        st.rerun()

                    except json.JSONDecodeError:
                        st.error("The model returned something that wasn't valid JSON. Try again.")
                    except Exception as exc:
                        st.error(f"Analysis failed: {exc}")

    with right:
        st.markdown(
            card(
                "What you'll get",
                bullet_rows(
                    [
                        "An ATS score out of 100",
                        "The skills a parser can actually read",
                        "Strengths worth keeping",
                        "Specific fixes, ordered by impact",
                        "Roles your experience lines up with",
                    ],
                    dot="info",
                ),
            ),
            unsafe_allow_html=True,
        )


# =========================================================
# PAGE — OVERVIEW
# =========================================================

elif st.session_state.page == "overview":

    st.markdown(
        topbar("Overview", "How your resume scores and what it says about you.", score),
        unsafe_allow_html=True,
    )

    if not data:
        empty_state("Upload a resume to see your score.")
    else:
        profile = '<div class="body-text">%s</div>' % esc(data.get("profile_summary", ""))

        st.markdown(
            f'<div class="grid g-score">'
            f'{card("Overall score", dial(score))}'
            f'{card("Profile summary", profile)}'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="card"><div class="grid g-3" style="margin:0">'
            f'{stat(len(skills), "skills detected")}'
            f'{stat(len(strengths), "strengths")}'
            f'{stat(len(improvements), "areas to fix")}'
            f'</div></div>',
            unsafe_allow_html=True,
        )


# =========================================================
# PAGE — SKILLS
# =========================================================

elif st.session_state.page == "skills":

    st.markdown(
        topbar("Skills", "What a parser pulled out, and where you're strong.", score),
        unsafe_allow_html=True,
    )

    if not data:
        empty_state("Upload a resume to see the skills it surfaces.")
    else:
        st.markdown(
            f'<div class="grid g-lead">'
            f'{card("Detected skills", pills(skills), count=len(skills))}'
            f'{card("Strengths", bullet_rows(strengths, dot="good"), count=len(strengths))}'
            f'</div>',
            unsafe_allow_html=True,
        )


# =========================================================
# PAGE — EXPERIENCE
# =========================================================

elif st.session_state.page == "experience":

    st.markdown(
        topbar("Experience", "Your history as the model reads it, and the roles it fits.", score),
        unsafe_allow_html=True,
    )

    if not data:
        empty_state("Upload a resume to see your experience breakdown.")
    else:
        role_rows = "".join(
            '<div class="role"><span>%s</span><span class="rank">%s</span></div>'
            % (esc(r), "best fit" if n == 1 else "#%d" % n)
            for n, r in enumerate(roles, 1)
        ) or '<div class="body-text">No roles suggested.</div>'

        experience = '<div class="body-text">%s</div>' % esc(data.get("experience_summary", ""))

        st.markdown(
            f'<div class="grid g-lead">'
            f'{card("Experience summary", experience)}'
            f'{card("Recommended roles", role_rows, count=len(roles))}'
            f'</div>',
            unsafe_allow_html=True,
        )


# =========================================================
# PAGE — IMPROVEMENTS
# =========================================================

elif st.session_state.page == "suggestions":

    st.markdown(
        topbar("Improvements", "Fix these first — they move the score the most.", score),
        unsafe_allow_html=True,
    )

    if not data:
        empty_state("Upload a resume to get specific fixes.")
    else:
        st.markdown(
            f'<div class="grid g-2">'
            f'{card("Areas to fix", bullet_rows(improvements, dot="warn"), count=len(improvements))}'
            f'{card("How to fix them", numbered_rows(tips), count=len(tips))}'
            f'</div>',
            unsafe_allow_html=True,
        )

        pdf_bytes = build_report_pdf(st.session_state.filename, score, data)
        st.download_button(
            "Download report (PDF)",
            data=pdf_bytes,
            file_name="resume-analysis.pdf",
            mime="application/pdf",
        )