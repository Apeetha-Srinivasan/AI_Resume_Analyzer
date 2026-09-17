import os
import json
import html
import hashlib
import re
from io import BytesIO
from textwrap import dedent
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
    --ink:       #24141B;
    --ink-soft:  #5F4A52;
    --muted:     #806B73;

    --line:      #E8D7DE;
    --canvas:    #FBF6F8;
    --surface:   #FFFFFF;

    --burgundy:  #941B3D;
    --burgundy-dark: #5A1027;
    --burgundy-soft: #F8E8EE;

    --rose:      #D94F7A;
    --rose-soft: #FCEEF3;

    --good:      #23845F;
    --good-soft: #EAF6F0;

    --warn:      #C58418;
    --warn-soft: #FFF5DF;

    --bad:       #C43D4B;
    --bad-soft:  #FBEAEC;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

body {
    font-size: 16px;
}

.stApp { background: var(--canvas); }
#MainMenu, footer { visibility: hidden; }

.block-container {
    padding: 1.25rem 2.25rem 3rem;
    max-width: 1320px;
}

/* Reduce Streamlit's top header height */
header[data-testid="stHeader"] {
    height: 32px;
    background: transparent;
}

/* Keep the sidebar collapse/expand control visible */
header[data-testid="stHeader"] button {
    top: 4px;
}

/* Remove excess top padding from the main content */
.block-container {
    padding-top: 0.8rem !important;
}

/* ---------------- sidebar ---------------- */

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #5A1027 0%,
        #6F1734 55%,
        #4A0D20 100%
    );
    border-right: none;
}

section[data-testid="stSidebar"] * {
    color: #FFF7FA;
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;

    font-family: 'Space Grotesk', sans-serif;
    font-size: 21px;
    font-weight: 700;

    padding: 4px 6px 20px;
}

.brand-mark {
    width: 34px;
    height: 34px;
    border-radius: 9px;

    background: linear-gradient(
        135deg,
        #D94F7A,
        #941B3D
    );

    display: grid;
    place-items: center;
    font-size: 17px;
}

.nav-label {
    font-family: 'Inter', sans-serif;

    font-size: 14px;
    font-weight: 600;

    color: #EAB9C8 !important;

    padding: 16px 8px 9px;
}

/* Sidebar buttons */

section[data-testid="stSidebar"] .stButton > button {
    background: transparent;
    border: none;
    border-radius: 10px;

    color: #EFD7DF;

    font-family: 'Inter', sans-serif;
    font-size: 17px;
    font-weight: 500;

    text-align: left;
    justify-content: flex-start;

    padding: 13px 14px;

    min-height: 46px;

    transition: all .15s ease;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.09);
    color: #FFFFFF;
}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #D94F7A;
    color: #FFFFFF;

    font-size: 17px;
    font-weight: 600;
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
.side-meta .sub { color: #C7A4B2 !important; }

/* ---------------- top bar ---------------- */

.topbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;

    gap: 20px;

    padding-top: 4px;
    padding-bottom: 18px;

    margin-bottom: 24px;

    border-bottom: 1px solid var(--line);
}

.topbar h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 32px;
    font-weight: 700;
    line-height: 1.25;

    color: var(--burgundy);

    margin: 0 0 8px;
}

.topbar p {
    font-family: 'Inter', sans-serif;
    font-size: 16px;
    line-height: 1.5;

    color: var(--ink-soft);
    margin: 0;
}

.chip {
    font-family: 'Inter', sans-serif;

    font-size: 14px;
    font-weight: 600;

    padding: 9px 16px;

    border-radius: 999px;

    white-space: nowrap;

    margin-top: 2px;
}

.chip-good {
    background: #F7E6EC;
    color: var(--burgundy);
}

.chip-warn {
    background: #FFF3DD;
    color: var(--warn);
}

.chip-bad {
    background: #FBE7EA;
    color: var(--bad);
}

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

    border: 1.5px solid #E4C8D2;
    border-radius: 14px;

    padding: 24px 26px;

    box-shadow: 0 2px 8px rgba(91, 16, 39, 0.03);
}

.card-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 17px;
    font-weight: 600;

    color: var(--burgundy);

    margin-bottom: 16px;
}

.card-title .count {
    color: var(--muted);
    font-weight: 500;
    margin-left: 6px;
}
.body-text {
    font-family: 'Inter', sans-serif;

    font-size: 16px;
    line-height: 1.7;

    color: var(--ink-soft);

    max-width: 75ch;
}

.profile-summary-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 26px;
    font-weight: 700;

    color: var(--burgundy);

    margin-bottom: 15px;
}

.profile-summary-text {
    font-family: 'Inter', sans-serif;

    font-size: 17px;
    font-weight: 400;

    line-height: 1.75;

    color: var(--ink-soft);

    max-width: 900px;
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

    font-size: 56px;
    font-weight: 700;

    line-height: 1;

    color: var(--burgundy);
}

.dial-den {
    font-size: 14px;
    color: var(--muted);
    margin-top: 6px;
}

.dial-verdict {
    text-align: center;

    font-family: 'Space Grotesk', sans-serif;

    font-size: 18px;
    font-weight: 700;

    color: var(--burgundy);

    margin-top: 18px;
}

.dial-note {
    text-align: center;

    font-size: 14px;

    color: var(--muted);

    margin-top: 5px;
}

/* ---------------- stat strip ---------------- */

.stat {
    border-left: 4px solid #D94F7A;

    padding-left: 18px;
    min-height: 68px;

    display: flex;
    flex-direction: column;
    justify-content: center;
}

.stat:nth-child(2) {
    border-left-color: #3D9AA3;
}

.stat:nth-child(3) {
    border-left-color: #D89A25;
}

.stat-num {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 32px;
    font-weight: 700;

    color: var(--burgundy);

    line-height: 1.1;
}

.stat-lab {
    font-family: 'Inter', sans-serif;

    font-size: 16px;
    font-weight: 500;

    color: var(--ink-soft);

    margin-top: 5px;
}
.stats-card {
    background: #FFFFFF;

    border: 1.5px solid #E4C8D2;
    border-radius: 14px;

    padding: 24px 28px;
}

/* ---------------- pills + lists ---------------- */

.pills {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
}

.pill {
    font-family: 'Inter', sans-serif;

    font-size: 14px;
    font-weight: 600;

    color: var(--burgundy);

    background: #F9E9EF;

    border: 1px solid #EBC7D3;

    border-radius: 8px;

    padding: 7px 13px;
}

.rows { display: flex; flex-direction: column; gap: 11px; }
.row {
    display: flex;

    gap: 11px;

    font-family: 'Inter', sans-serif;

    font-size: 15px;

    line-height: 1.65;

    color: var(--ink-soft);
}
.row .dot {
    flex: 0 0 auto;
    width: 6px; height: 6px;
    border-radius: 50%;
    margin-top: 8px;
}
.dot-good {
    background: #23845F;
}

.dot-warn {
    background: #C58418;
}

.dot-info {
    background: #941B3D;
}

.step { display: flex; gap: 12px; align-items: flex-start; }
.step-n {
    flex: 0 0 auto;
    width: 22px; height: 22px;
    border-radius: 6px;
    background: #F8EAF0;
    color: var(--burgundy);
    font-size: 11.5px;
    font-weight: 700;
    display: grid; place-items: center;
    margin-top: 1px;
}

.role {
    display: flex;

    justify-content: space-between;
    align-items: center;

    padding: 15px 4px;

    border-bottom: 1px solid var(--line);

    font-family: 'Inter', sans-serif;

    font-size: 15px;
    color: var(--ink);

    font-weight: 600;
}

.role:last-child {
    border-bottom: none;
}

.role .rank {
    font-size: 13px;
    color: var(--burgundy);

    background: var(--burgundy-soft);

    padding: 5px 9px;
    border-radius: 999px;

    font-weight: 600;
}

/* ---------------- introduction ---------------- */

.intro-box {
    display: flex;
    align-items: flex-start;
    gap: 18px;
    background: linear-gradient(135deg, #FFF9FB, #F8EDF2);
    border: 1px solid #EBD6DF;
    border-radius: 14px;
    padding: 24px 26px;
    margin-bottom: 22px;
    box-shadow: 0 4px 18px rgba(53, 21, 34, 0.04);
}

.intro-icon {
    flex: 0 0 auto;
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border-radius: 11px;
    background: linear-gradient(135deg, #D05A82, #8E3157);
    color: #FFFFFF;
    font-size: 20px;
    font-weight: 700;
}

.intro-content {
    min-width: 0;
}

.intro-box h2 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 23px;
    font-weight: 700;
    color: #24141B;
    margin: 0 0 8px;
    letter-spacing: -0.02em;
}

.intro-box p {
    font-family: 'Inter', sans-serif;
    font-size: 15.5px;
    font-weight: 400;
    line-height: 1.7;
    color: #5F4A52;
    margin: 0;
    max-width: 980px;
}

.intro-points {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 18px;
    margin-top: 15px;
    font-size: 13.5px;
    font-weight: 600;
    color: #7A294B;
}

@media (max-width: 700px) {
    .intro-box { padding: 20px; }
    .intro-box h2 { font-size: 20px; }
    .intro-box p { font-size: 14.5px; }
}

/* ---------------- empty state ---------------- */

.empty {
    background: var(--surface);
    border: 1px dashed #DFCBD3;
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
    background: var(--burgundy);
    color: #fff;
    border: none;
    border-radius: 9px;
    height: 44px;
    font-weight: 600;
    font-size: 15px;
}
div[data-testid="stMain"] .stButton > button:hover { background: #7D294D; }
div[data-testid="stMain"] .stButton > button[kind="secondary"] {
    background: var(--surface);
    color: var(--ink-soft);
    border: 1px solid var(--line);
}

.improvement-tip {
    display: flex;
    align-items: flex-start;

    gap: 16px;

    background: #FFF7F9;

    border: 1.5px solid #E7B7C7;
    border-radius: 14px;

    padding: 20px 24px;

    margin-top: 20px;
}

.tip-icon {
    width: 42px;
    height: 42px;

    border-radius: 10px;

    background: #F8DDE6;

    display: grid;
    place-items: center;

    font-size: 21px;

    flex-shrink: 0;
}

.tip-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 18px;
    font-weight: 700;

    color: var(--burgundy);

    margin-bottom: 5px;
}

.tip-text {
    font-family: 'Inter', sans-serif;

    font-size: 15px;
    line-height: 1.6;

    color: var(--ink-soft);
}

</style>
"""

def render_html(content):
    """Render HTML through Streamlit markdown while removing Python indentation.

    This keeps one shared CSS context for the whole app and prevents indented
    HTML from being interpreted as a Markdown code block.
    """
    cleaned = dedent(str(content)).strip()
    cleaned = re.sub(r"(?m)^[ \t]+", "", cleaned)
    st.markdown(cleaned, unsafe_allow_html=True)


render_html(CSS)


# =========================================================
# HELPERS
# =========================================================

def esc(value):
    """Model output goes into raw HTML, so escape it."""
    return html.escape(str(value))


def tone(score):
    if score >= 80:
        return "good", "#941B3D"
    if score >= 60:
        return "warn", "#C58418"
    return "bad", "#C43D4B"


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
    render_html(
        f'<div class="empty"><h3>No analysis yet</h3><p>{esc(message)}</p></div>',
            )


def build_report_pdf(filename, score, data):
    """Render the analysis as a one-file PDF report, returned as bytes."""

    ink = HexColor("#24141B")
    ink_soft = HexColor("#5F4A52")
    muted = HexColor("#8A737C")
    indigo = HexColor("#9A3D63")
    _, score_hex = tone(score)
    score_colour = HexColor(score_hex)
    line = HexColor("#E9DDE2")

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
    key = os.getenv("GOOGLE_API_KEY", "")

    if not key:
        try:
            key = st.secrets.get("GOOGLE_API_KEY", "")
        except Exception:
            key = ""

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
    render_html(
        '<div class="brand"><span class="brand-mark">📄</span>Resume AI</div>',
            )

    if st.button(
        "Upload resume",
        use_container_width=True,
        type="primary" if st.session_state.page == "analyze" else "secondary",
    ):
        st.session_state.page = "analyze"
        st.rerun()

    render_html('<div class="nav-label">Analysis</div>')

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
        render_html(
            f'<div class="side-meta"><span class="fname">'
            f'{esc(st.session_state.filename)}</span>'
            f'<span class="sub">Analyzed with {esc(MODEL)}</span></div>',
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

    render_html(
        topbar(
            "Upload resume",
            "Drop in a PDF and we'll score it the way an applicant tracking system would.",
            score,
        ),
            )

    render_html(
        dedent("""
        <div class="intro-box">
            <div class="intro-icon">✦</div>
            <div class="intro-content">
                <h2>Understand your resume before you apply</h2>
                <p>
                    Resume AI Analyzer uses AI to review your resume and show you how it may be interpreted by an Applicant Tracking System (ATS).
                    Get an overall score, discover detected skills, understand your strengths, identify areas to improve, and explore roles that match your experience.
                </p>
                <div class="intro-points">
                    <span>✓ ATS score</span>
                    <span>✓ Skills detected</span>
                    <span>✓ Strengths & gaps</span>
                    <span>✓ Role suggestions</span>
                </div>
            </div>
        </div>
        """),
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
        render_html(
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
                    )


# =========================================================
# PAGE — OVERVIEW
# =========================================================

elif st.session_state.page == "overview":

    render_html(
        topbar(
            "Overview",
            "How your resume scores and what it says about you.",
            score
        ),
            )

    if not data:

        empty_state("Upload a resume to see your score.")

    else:

        profile = data.get("profile_summary", "")

        render_html(
            dedent(f"""
            <div class="grid g-score">

                <div class="card">

                    <div class="card-title">
                        Overall score
                    </div>

                    {dial(score)}

                </div>

                <div class="card">

                    <div class="profile-summary-title">
                        Profile Summary
                    </div>

                    <div class="profile-summary-text">
                        {esc(profile)}
                    </div>

                </div>

            </div>
            """),
                    )

        render_html(
            dedent(f"""
            <div class="stats-card">

                <div class="grid g-3" style="margin:0">

                    {stat(len(skills), "skills detected")}

                    {stat(len(strengths), "strengths")}

                    {stat(len(improvements), "areas to fix")}

                </div>

            </div>
            """),
                    )

    


# =========================================================
# PAGE — SKILLS
# =========================================================

elif st.session_state.page == "skills":

    render_html(
        topbar(
            "Skills",
            "The key skills we found in your resume.",
            score
        ),
            )

    if not data:

        empty_state(
            "Upload a resume to see the skills it surfaces."
        )

    else:

        render_html(
            dedent(f"""
            <div class="grid g-lead">

                {card(
                    "Detected Skills",
                    pills(skills),
                    count=len(skills)
                )}

                {card(
                    "Top Strengths",
                    bullet_rows(
                        strengths,
                        dot="good"
                    ),
                    count=len(strengths)
                )}

            </div>
            """),
                    )

        render_html(
            dedent(f"""
            <div class="grid g-2">

                {card(
                    "Skills Overview",
                    '<div class="body-text">'
                    'These are the technical and professional '
                    'skills identified from your resume.'
                    '</div>'
                )}

                {card(
                    "What to Improve",
                    bullet_rows(
                        improvements,
                        dot="warn"
                    ),
                    count=len(improvements)
                )}

            </div>
            """),
                    )


# =========================================================
# PAGE — EXPERIENCE
# =========================================================

elif st.session_state.page == "experience":

    render_html(
        topbar(
            "Experience",
            "Your professional history and the roles it aligns with.",
            score
        ),
            )

    if not data:

        empty_state(
            "Upload a resume to see your experience breakdown."
        )

    else:

        experience = data.get(
            "experience_summary",
            "Not available."
        )

        role_rows = "".join(
            f'<div class="role"><span>{esc(r)}</span>'
            f'<span class="rank">{"best fit" if n == 1 else "#" + str(n)}</span></div>'
            for n, r in enumerate(roles, 1)
        )

        if not role_rows:

            role_rows = """
            <div class="body-text">
                No roles suggested.
            </div>
            """

        render_html(
            dedent(f"""
            <div class="grid g-lead">

                <div class="card">

                    <div class="card-title">
                        Experience Summary
                    </div>

                    <div class="profile-summary-text">
                        {esc(experience)}
                    </div>

                </div>

                <div class="card">

                    <div class="card-title">
                        Recommended Roles
                        <span class="count">
                            {len(roles)}
                        </span>
                    </div>

                    {role_rows}

                </div>

            </div>
            """),
                    )


# =========================================================
# PAGE — IMPROVEMENTS
# =========================================================

elif st.session_state.page == "suggestions":

    render_html(
        topbar(
            "Improvements",
            "Actionable suggestions to make your resume stronger.",
            score
        ),
            )

    if not data:

        empty_state(
            "Upload a resume to get specific fixes."
        )

    else:

        render_html(
            dedent(f"""
            <div class="grid g-2">

                {card(
                    "Areas to Fix",
                    bullet_rows(
                        improvements,
                        dot="warn"
                    ),
                    count=len(improvements)
                )}

                {card(
                    "How to Fix Them",
                    numbered_rows(tips),
                    count=len(tips)
                )}

            </div>
            """),
                    )

        render_html(
            dedent("""
            <div class="improvement-tip">

                <div class="tip-icon">
                    💡
                </div>

                <div>
                    <div class="tip-title">
                        Pro Tip
                    </div>

                    <div class="tip-text">
                        Focus on the highest-impact improvements first.
                        Small changes to wording, structure and
                        measurable achievements can make your resume
                        easier to understand.
                    </div>
                </div>

            </div>
            """),
                    )

        pdf_bytes = build_report_pdf(
            st.session_state.filename,
            score,
            data
        )

        st.download_button(
            "Download report (PDF)",
            data=pdf_bytes,
            file_name="resume-analysis.pdf",
            mime="application/pdf",
        )