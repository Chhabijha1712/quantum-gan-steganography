"""
streamlit_app.py — polished, recruiter-ready browser UI
--------------------------------------------------------------
Same send.py/receive.py backend — only the presentation layer changed.
A calm, light canvas; a fixed (non-spinning) quantum-lock mark as the one
memorable visual; three colour-coded section tabs (Sender / Receiver /
How It Works); consistent card system for every upload/key field; and
motion reserved for things the person actually does (hover a button,
watch the live pipeline run) rather than scattered on every element.

Run:
    streamlit run streamlit_app.py
"""

import os
import re
import sys
import time
import threading

import streamlit as st

from config import CFG
import send as send_module
import receive as receive_module
from key_exchange import generate_receiver_keypair, serialize_private_key, serialize_public_key


st.set_page_config(page_title="Quantum-GAN Steganography", page_icon="🔐", layout="wide")

# ============================== STYLING ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --ink: #10162b;
    --body: #3d4560;
    --muted: #6b7290;
    --canvas: #eef1f8;
    --card: #ffffff;
    --border: #dde2ef;
    --sender: #2f5dd4;
    --sender-soft: #e8edfd;
    --sender-mid: #c6d4fb;
    --receiver: #16a866;
    --receiver-soft: #e3f8ee;
    --receiver-mid: #b9ecd3;
    --quantum: #7c4dd6;
    --quantum-soft: #f1e9fc;
    --quantum-mid: #dfc9f7;
    --gold: #e8a317;
    --navbar: #10162b;
}

/* Pin Streamlit's own theme tokens to our light palette so nothing goes
   invisible when the browser/OS or user's Streamlit setting is dark —
   most native widgets (alerts, expanders, code blocks) style themselves
   from these variables internally. */
:root, .stApp {
    --background-color: #eef1f8 !important;
    --secondary-background-color: #ffffff !important;
    --text-color: #10162b !important;
    --primary-color: #2f5dd4 !important;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 16.5px; }
h1, h2, h3, h4, h5, h6 { font-family: 'Space Grotesk', sans-serif; color: var(--ink) !important; }

@media (prefers-reduced-motion: reduce) {
    * { animation-duration: 0.001ms !important; animation-iteration-count: 1 !important; transition-duration: 0.001ms !important; }
}

/* ---- Page canvas ---- */
.stApp { background: var(--canvas); }
[data-testid="stHeader"] { background: transparent; }
.block-container {
    max-width: 1540px;
    margin: 0 auto;
    padding: 0.6rem 2.6rem 3.2rem 2.6rem !important;
}
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li { color: var(--body); font-size: 1.02rem; line-height: 1.6; }
label p { color: var(--ink) !important; font-weight: 600 !important; font-size: 1.02rem !important; }
[data-testid="stCaptionContainer"] { color: var(--muted) !important; font-size: 0.92rem !important; }

/* ---- Hero title (biggest text on the page, with icon badge + tagline) ---- */
.hero-title {
    text-align: center;
    padding: 2.2rem 1.8rem 2rem 1.8rem;
    margin-bottom: 2rem;
    border-radius: 22px;
    background: linear-gradient(120deg, var(--sender-soft) 0%, var(--quantum-soft) 50%, var(--receiver-soft) 100%);
    border: 1.5px solid var(--sender-mid);
    box-shadow: 0 10px 28px rgba(47,93,212,0.10);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.65rem;
    opacity: 0;
    animation: dropIn 0.5s ease-out forwards;
}
.hero-title .hero-top {
    display: flex; align-items: center; justify-content: center; gap: 1.1rem;
    flex-wrap: wrap;
}
.hero-title .hero-icon-badge {
    width: 72px; height: 72px; border-radius: 20px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, var(--sender), var(--quantum));
    box-shadow: 0 8px 20px rgba(124,77,214,0.35), 0 0 0 6px rgba(124,77,214,0.08);
}
.hero-title .hero-icon-badge svg { width: 38px; height: 38px; display: block; }
.hero-title h1 {
    font-size: 2.75rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.16;
    max-width: 780px;
    background: linear-gradient(100deg, var(--sender) 0%, var(--quantum) 55%, var(--receiver) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: var(--ink);
}
.hero-title .hero-tagline {
    margin: 0.2rem 0 0 0;
    font-size: 1.05rem;
    font-weight: 500;
    color: var(--body);
    max-width: 620px;
}
@keyframes dropIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }

/* Three separate light "card" tabs instead of one dark bar — each tab
   gets its own soft tint (blue / green / violet) so they read as distinct
   info-card buttons, with a decent gap between them. Every text color
   below is set explicitly (not inherited) so it can never be swallowed
   by the user's light/dark theme setting. */
div[data-testid="stTabs"] { margin-top: 0.2rem; margin-bottom: 2.3rem; }
div[data-testid="stTabs"] div[role="tablist"],
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-radius: 0 !important;
    gap: 1.1rem !important;
    display: flex !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    box-shadow: none !important;
}
div[data-testid="stTabs"] button[role="tab"],
[data-baseweb="tab"] {
    flex: 1 1 0 !important;
    justify-content: center !important;
    border-radius: 18px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.65rem !important;
    background: var(--sender-soft) !important;
    border: 2px solid var(--sender-mid) !important;
    padding: 1.7rem 1.5rem !important;
    min-height: 84px;
    box-shadow: 0 4px 14px rgba(16,22,43,0.06);
    transition: transform 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
}
div[data-testid="stTabs"] button[role="tab"] p { font-size: 1.65rem !important; font-weight: 700 !important; color: var(--sender) !important; }
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) { background: var(--receiver-soft) !important; border-color: var(--receiver-mid) !important; }
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) p { color: var(--receiver) !important; }
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) { background: var(--quantum-soft) !important; border-color: var(--quantum-mid) !important; }
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) p { color: var(--quantum) !important; }
div[data-testid="stTabs"] button[role="tab"]:hover { transform: translateY(-3px); box-shadow: 0 10px 22px rgba(16,22,43,0.12); }
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, var(--sender), #4a7bea) !important;
    border-color: var(--sender) !important;
    box-shadow: 0 10px 24px rgba(47,93,212,0.32);
    transform: translateY(-2px);
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p { color: #ffffff !important; }
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)[aria-selected="true"] {
    background: linear-gradient(135deg, var(--receiver), #22c47f) !important;
    border-color: var(--receiver) !important;
    box-shadow: 0 10px 24px rgba(22,168,102,0.32);
}
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)[aria-selected="true"] {
    background: linear-gradient(135deg, var(--quantum), #9a6ae8) !important;
    border-color: var(--quantum) !important;
    box-shadow: 0 10px 24px rgba(124,77,214,0.32);
}
[data-baseweb="tab-highlight"] { display: none !important; height: 0 !important; }
[data-baseweb="tab-border"] { display: none !important; }
[data-baseweb="tab-panel"] { padding-top: 0 !important; }


/* ---- Capability strip ---- */
.capability-strip {
    display: flex; flex-wrap: wrap; gap: 0.6rem;
    padding: 0.2rem 0.1rem 1.8rem 0.1rem;
}
.capability-strip span {
    font-size: 0.86rem; font-weight: 600; color: var(--sender);
    background: var(--sender-soft); border: 1px solid var(--sender-mid);
    border-radius: 20px; padding: 0.35rem 0.9rem 0.35rem 0.7rem;
    display: inline-flex; align-items: center; gap: 0.45rem;
    transition: transform 0.15s ease;
}
.capability-strip span::before { content: "\\2699"; font-size: 0.8rem; }
.capability-strip span:hover { transform: translateY(-2px); }

/* ---- Big bold page-heading banner (per-page, light highlight) ---- */
.page-banner {
    display: flex; align-items: center; gap: 1rem;
    border-radius: 16px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.6rem;
    opacity: 0;
    animation: bannerIn 0.5s ease-out 0.05s forwards;
}
@keyframes bannerIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.page-banner .emoji { font-size: 2.3rem; line-height: 1; flex-shrink: 0; }
.page-banner h2 { margin: 0; font-size: 1.9rem; font-weight: 700; letter-spacing: -0.01em; }
.page-banner p { margin: 0.3rem 0 0 0; font-size: 1.02rem; color: var(--body); max-width: 700px; }
.page-banner.blue { background: linear-gradient(120deg, var(--sender-soft), #ffffff); border: 1.5px solid var(--sender-mid); }
.page-banner.blue h2 { color: var(--sender) !important; }
.page-banner.green { background: linear-gradient(120deg, var(--receiver-soft), #ffffff); border: 1.5px solid var(--receiver-mid); }
.page-banner.green h2 { color: var(--receiver) !important; }
.page-banner.violet { background: linear-gradient(120deg, var(--quantum-soft), #ffffff); border: 1.5px solid var(--quantum-mid); }
.page-banner.violet h2 { color: var(--quantum) !important; }

/* ---- Sub-section step headings ---- */
.step-heading {
    display: flex; align-items: center; gap: 0.7rem;
    margin: 0.4rem 0 1rem 0;
}
.step-heading .num {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 1.02rem; color: #ffffff; flex-shrink: 0;
}
.step-heading.blue .num { background: var(--sender); }
.step-heading.green .num { background: var(--receiver); }
.step-heading h3 { margin: 0; font-size: 1.3rem; font-weight: 700; }
.step-heading .hint { font-size: 0.88rem; color: var(--muted); margin-left: 0.3rem; }

/* ---- Cards / panels ---- */
.panel {
    background: var(--card); border: 1.5px solid var(--border); border-radius: 14px;
    padding: 1.3rem 1.5rem; margin-bottom: 1.1rem;
    box-shadow: 0 2px 10px rgba(16,22,43,0.04);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.panel:hover { box-shadow: 0 6px 20px rgba(16,22,43,0.08); }

/* ---- Info cards (used to frame each upload / key field) ---- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 0.2rem 0.1rem 0.6rem 0.1rem !important;
    box-shadow: 0 2px 10px rgba(16,22,43,0.04);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
    margin-bottom: 1.1rem;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 8px 22px rgba(16,22,43,0.08);
    border-color: var(--sender-mid) !important;
}
.info-card-header {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 0.7rem 0.9rem 0.15rem 0.9rem;
}
.info-card-header .icon-badge {
    width: 42px; height: 42px; border-radius: 12px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    background: var(--sender-soft);
}
.info-card-header.blue .icon-badge { background: var(--sender-soft); }
.info-card-header.green .icon-badge { background: var(--receiver-soft); }
.info-card-header.violet .icon-badge { background: var(--quantum-soft); }
.info-card-header .text h4 { margin: 0; font-size: 1.02rem; font-weight: 700; color: var(--ink) !important; }
.info-card-header .text p { margin: 0.15rem 0 0 0; font-size: 0.86rem; color: var(--muted); line-height: 1.4; }

/* ---- Buttons ---- */
.stButton button, .stDownloadButton button {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700 !important;
    font-size: 1.02rem !important;
    border-radius: 12px !important;
    padding: 0.7rem 1.1rem !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.stButton button[kind="primary"] {
    background: linear-gradient(120deg, #3a63e0, #2f5dd4) !important;
    border: none !important; color: #ffffff !important;
    box-shadow: 0 5px 16px rgba(47,93,212,0.35);
}
.stButton button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(47,93,212,0.45); }
.stButton button[kind="secondary"] {
    background: #ffffff !important; border: 2px solid var(--sender) !important; color: var(--sender) !important;
}
.stButton button[kind="secondary"]:hover { background: var(--sender-soft) !important; transform: translateY(-2px); }
.stDownloadButton button {
    background: #ffffff !important; border: 2px solid var(--receiver) !important; color: var(--receiver) !important;
}
.stDownloadButton button:hover { background: var(--receiver-soft) !important; transform: translateY(-2px); }
.stButton button:active, .stDownloadButton button:active { transform: translateY(0); }

/* ---- File uploader ---- */
[data-testid="stFileUploaderDropzone"] {
    background: #ffffff !important; border: 2px dashed var(--sender-mid) !important;
    border-radius: 14px !important; transition: border-color 0.2s ease, background 0.2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--sender) !important; background: var(--sender-soft) !important; }
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] p { color: var(--body) !important; }
[data-testid="stFileUploaderDropzone"] svg { fill: var(--muted) !important; }
[data-testid="stFileUploaderDropzone"] button {
    background: #ffffff !important; color: var(--sender) !important;
    border: 1.5px solid var(--sender-mid) !important; border-radius: 8px !important;
}

/* ---- Uploaded-file chip (shown after a file is picked) ---- */
[data-testid="stFileUploaderFile"],
div[class*="uploadedFile"] {
    background: var(--navbar) !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderFile"] *,
div[class*="uploadedFile"] * {
    color: #ffffff !important;
    opacity: 1 !important;
}
[data-testid="stFileUploaderFileName"] { color: #ffffff !important; font-weight: 600 !important; }
[data-testid="stFileUploaderFile"] small,
div[class*="uploadedFile"] small { color: #c7cce3 !important; }
[data-testid="stFileUploaderDeleteBtn"] svg { fill: #ffffff !important; }

/* ---- Text input ---- */
.stTextInput input {
    background: #ffffff !important; border: 1.5px solid var(--border) !important; color: var(--ink) !important;
    border-radius: 10px !important; font-size: 1.02rem !important; padding: 0.55rem 0.8rem !important;
}
.stTextInput input:focus { border-color: var(--sender) !important; box-shadow: 0 0 0 3px var(--sender-soft) !important; }

/* ---- Metrics / alerts / expander / code / divider / images ---- */
div[data-testid="stMetric"] {
    background: #ffffff; border: 1.5px solid var(--border); border-radius: 14px; padding: 1rem 1.2rem;
    box-shadow: 0 2px 10px rgba(16,22,43,0.04);
}
div[data-testid="stMetric"] label { color: var(--muted) !important; font-size: 0.9rem !important; }
div[data-testid="stMetric"] div { color: var(--sender) !important; font-size: 1.5rem !important; font-weight: 700 !important; }
[data-testid="stAlert"] { border-radius: 12px; font-size: 1rem; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] div { color: var(--ink) !important; }
[data-testid="stExpander"] { background: #ffffff; border: 1.5px solid var(--border) !important; border-radius: 14px !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span { color: var(--ink) !important; font-weight: 600 !important; }
.stCodeBlock, pre { border-radius: 12px !important; border: 1.5px solid var(--border) !important; }
.stCodeBlock, .stCodeBlock pre, .stCodeBlock code { background: #f6f8fc !important; color: var(--ink) !important; }
hr { border-color: var(--border) !important; }
[data-testid="stImage"] img { border-radius: 12px; border: 1.5px solid var(--border); }

/* ---- Formal step-tracker (live progress) ---- */
.stepper {
    display: flex; align-items: flex-start; justify-content: space-between;
    background: #ffffff; border: 1.5px solid var(--border); border-radius: 14px;
    padding: 1.4rem 1.6rem 1.2rem 1.6rem; margin-bottom: 1rem;
    box-shadow: 0 2px 10px rgba(16,22,43,0.04);
}
.step { display: flex; flex-direction: column; align-items: center; min-width: 84px; }
.step-circle {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.95rem; border: 2.5px solid var(--border); color: var(--muted);
    background: #f6f8fc; transition: all 0.25s ease;
}
.step.active .step-circle {
    border-color: var(--sender); background: var(--sender); color: #ffffff;
    box-shadow: 0 0 0 5px var(--sender-soft); animation: pulse 1.4s infinite;
}
.step.completed .step-circle { border-color: var(--receiver); background: var(--receiver); color: #ffffff; }
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(47,93,212,0.35); }
    70% { box-shadow: 0 0 0 10px rgba(47,93,212,0); }
    100% { box-shadow: 0 0 0 0 rgba(47,93,212,0); }
}
.step-label { margin-top: 0.55rem; font-size: 0.84rem; font-weight: 600; color: var(--ink); text-align: center; line-height: 1.25; }
.step.pending .step-label { color: var(--muted); }
.step-line { flex: 1; height: 3px; background: var(--border); margin: 19px 6px 0 6px; border-radius: 2px; transition: background 0.3s ease; }
.step-line.completed { background: var(--receiver); }
.log-title { font-size: 0.95rem; font-weight: 700; color: var(--ink); margin: 0.3rem 0 0.5rem 0.1rem; }

/* ---- How-it-works visual pipeline strip ---- */
.flow-card {
    background: #ffffff; border: 1.5px solid var(--border); border-radius: 14px;
    padding: 0.7rem 0.7rem 0.85rem 0.7rem; text-align: center;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.flow-card:hover { border-color: var(--quantum); box-shadow: 0 8px 20px rgba(124,77,214,0.12); }
.flow-card img { border-radius: 10px; width: 100%; display: block; }
.flow-card .flow-label { margin-top: 0.6rem; font-size: 0.92rem; font-weight: 700; color: var(--ink); }
.flow-card .flow-sublabel { font-size: 0.82rem; color: var(--muted); margin-top: 0.15rem; }
.flow-badge-wrap { display: flex; align-items: center; justify-content: center; height: 100%; min-height: 130px; }
.flow-badge {
    width: 42px; height: 42px; border-radius: 50%; background: var(--sender); color: #ffffff;
    display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.15rem; flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(47,93,212,0.3);
}
.flow-badge.green { background: var(--receiver); box-shadow: 0 4px 12px rgba(22,168,102,0.3); }

/* ---- Scenario storytelling ---- */
.scenario-banner {
    background: linear-gradient(120deg, var(--quantum-soft), #ffffff);
    border: 1.5px solid var(--quantum-mid); border-radius: 16px;
    padding: 1.3rem 1.6rem; margin: 0.3rem 0 1.6rem 0;
    display: flex; align-items: center; gap: 1.1rem;
}
.scenario-banner .tag {
    background: var(--gold); color: #ffffff; font-size: 0.8rem; font-weight: 700;
    padding: 0.35rem 0.8rem;
    border-radius: 20px; flex-shrink: 0;
}
.scenario-banner p { color: var(--ink); font-size: 1rem; margin: 0; line-height: 1.6; }

.stage-heading { display: flex; align-items: baseline; gap: 0.7rem; margin: 2rem 0 0.9rem 0; }
.stage-heading .stage-num {
    width: 30px; height: 30px; border-radius: 50%; background: var(--sender); color: #fff;
    display: inline-flex; align-items: center; justify-content: center; font-size: 0.86rem; font-weight: 700; flex-shrink: 0;
}
.stage-heading.receiver .stage-num { background: var(--receiver); }
.stage-heading h4 { margin: 0; font-size: 1.28rem; color: var(--ink) !important; font-weight: 700; }
.stage-heading .stage-sub { font-size: 0.88rem; color: var(--muted); }

.metric-pill-row { display: flex; gap: 0.7rem; flex-wrap: wrap; margin: 0.9rem 0 0.3rem 0; }
.metric-pill {
    background: var(--sender-soft); border: 1.5px solid var(--sender-mid); border-radius: 20px;
    padding: 0.45rem 1rem; font-size: 0.86rem; color: var(--sender); font-weight: 700;
}

.guarantee-row { display: flex; gap: 1.1rem; margin-top: 0.6rem; }
.guarantee-card { flex: 1; border-radius: 14px; padding: 1.2rem 1.35rem; border: 1.5px solid var(--border); transition: box-shadow 0.2s ease; }
.guarantee-card.a { background: var(--sender-soft); border-color: var(--sender-mid); }
.guarantee-card.b { background: var(--receiver-soft); border-color: var(--receiver-mid); }
.guarantee-card:hover { box-shadow: 0 8px 18px rgba(16,22,43,0.08); }
.guarantee-card h5 { margin: 0 0 0.4rem 0; font-size: 1.05rem; color: var(--ink) !important; display: flex; align-items: center; gap: 0.45rem; font-weight: 700; }
.guarantee-card p { margin: 0; font-size: 0.92rem; color: var(--body); line-height: 1.6; }

.skills-strip { margin-top: 2.2rem; padding-top: 1.4rem; border-top: 2px solid var(--border); }
.skills-strip .skills-title { font-size: 1.05rem; font-weight: 700; color: var(--ink); margin-bottom: 0.9rem; }
.tech-badge-row { display: flex; flex-wrap: wrap; gap: 0.7rem; }
.tech-badge {
    background: #ffffff; border: 1.5px solid var(--border); border-radius: 12px;
    padding: 0.65rem 0.95rem; font-size: 0.88rem; color: var(--body); min-width: 170px; flex: 1;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.tech-badge:hover { border-color: var(--quantum); box-shadow: 0 8px 18px rgba(124,77,214,0.12); }
.tech-badge b { display: block; color: var(--ink); font-size: 0.95rem; margin-bottom: 0.2rem; }
</style>
""", unsafe_allow_html=True)

# ============================== HERO TITLE ==============================
st.markdown("""
<div class="hero-title">
    <div class="hero-top">
        <div class="hero-icon-badge">
            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="24" cy="24" rx="20" ry="8" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.6"/>
                <ellipse cx="24" cy="24" rx="20" ry="8" stroke="#ffffff" stroke-opacity="0.32" stroke-width="1.6" transform="rotate(60 24 24)"/>
                <ellipse cx="24" cy="24" rx="20" ry="8" stroke="#ffffff" stroke-opacity="0.32" stroke-width="1.6" transform="rotate(120 24 24)"/>
                <rect x="15.5" y="21" width="17" height="14" rx="3.5" fill="#ffffff"/>
                <path d="M18.7 21v-4.2a5.3 5.3 0 0 1 10.6 0V21" stroke="#ffffff" stroke-width="2.6" fill="none" stroke-linecap="round"/>
                <circle cx="24" cy="27" r="2.1" fill="#2f5dd4"/>
            </svg>
        </div>
        <h1>Quantum Key Driven Image Steganography &amp; Steganalysis</h1>
    </div>
    <p class="hero-tagline">Hide a classified image inside an ordinary photo — protected end-to-end by a
    quantum-random key, RSA, AES, and an adversarially trained GAN.</p>
</div>
""", unsafe_allow_html=True)

# ============================== TABS ==============================
tab_send, tab_receive, tab_about = st.tabs(["📤  Sender", "📥  Receiver", "🧭  How It Works"])

st.markdown("""
<div class="capability-strip">
    <span>Quantum Key Generation</span>
    <span>RSA-2048 Key Exchange</span>
    <span>AES-128 CTR Encryption</span>
    <span>GAN-Based Steganography</span>
    <span>Adversarial Discriminator Training</span>
</div>
""", unsafe_allow_html=True)


def save_uploaded_file(uploaded_file, target_dir, filename):
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


UPLOAD_DIR = os.path.join(CFG.MESSAGES_DIR, "_uploads")
DEMO_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_assets")


def flow_card(col, image_path, label, sublabel=""):
    with col:
        st.image(image_path, use_container_width=True)
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div class="flow-label">{label}</div>'
            + (f'<div class="flow-sublabel">{sublabel}</div>' if sublabel else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def flow_badge(col, symbol, green=False):
    with col:
        cls = "flow-badge green" if green else "flow-badge"
        st.markdown(
            f'<div class="flow-badge-wrap"><div class="{cls}">{symbol}</div></div>',
            unsafe_allow_html=True,
        )


def page_banner(color, emoji, title, subtitle):
    st.markdown(
        f'<div class="page-banner {color}"><div class="emoji">{emoji}</div>'
        f'<div><h2>{title}</h2><p>{subtitle}</p></div></div>',
        unsafe_allow_html=True,
    )


def step_heading(color, number, title, hint=""):
    st.markdown(
        f'<div class="step-heading {color}"><div class="num">{number}</div>'
        f'<h3>{title}</h3>' + (f'<span class="hint">{hint}</span>' if hint else "") + '</div>',
        unsafe_allow_html=True,
    )


def info_card_header(color, icon, title, desc):
    st.markdown(
        f'<div class="info-card-header {color}"><div class="icon-badge">{icon}</div>'
        f'<div class="text"><h4>{title}</h4><p>{desc}</p></div></div>',
        unsafe_allow_html=True,
    )


SEND_STEPS = [
    ("generating a fresh quantum-assisted aes key", "Quantum Key\nGeneration"),
    ("wrapping the aes key", "RSA Key\nWrap"),
    ("aes-encrypting", "AES\nEncryption"),
    ("running the gan encoder", "GAN\nEmbedding"),
]
RECEIVE_STEPS = [
    ("unpacking message bundle", "Unpack\nMessage"),
    ("unwrapping the aes key", "RSA Key\nUnwrap"),
    ("aes-decrypting", "AES\nDecryption"),
    ("loading trained decoder", "GAN\nDecoding"),
]


def render_stepper(steps, log_text, done=False):
    low = log_text.lower()
    current = -1
    for i, (kw, _) in enumerate(steps):
        if kw in low:
            current = i
    parts = []
    for i, (_, label) in enumerate(steps):
        label_html = label.replace("\n", "<br/>")
        if done or i < current:
            state, circle = "completed", "&#10003;"
        elif i == current:
            state, circle = "active", str(i + 1)
        else:
            state, circle = "pending", str(i + 1)
        parts.append(
            f'<div class="step {state}"><div class="step-circle">{circle}</div>'
            f'<div class="step-label">{label_html}</div></div>'
        )
        if i < len(steps) - 1:
            line_state = "completed" if (done or i < current) else ""
            parts.append(f'<div class="step-line {line_state}"></div>')
    return f'<div class="stepper">{"".join(parts)}</div>'


def run_with_live_feedback(steps, fn, *args, **kwargs):
    """Runs fn in a background thread; streams a formal step-tracker plus
    a plain processing log into the page while it runs. Purely cosmetic --
    fn's actual behavior/return value is untouched."""
    log_lines = []
    result_holder, error_holder = {}, {}

    class LiveWriter:
        def write(self, s):
            log_lines.append(s)

        def flush(self):
            pass

    def target():
        old_stdout = sys.stdout
        sys.stdout = LiveWriter()
        try:
            result_holder["value"] = fn(*args, **kwargs)
        except Exception as e:
            error_holder["error"] = e
        finally:
            sys.stdout = old_stdout

    thread = threading.Thread(target=target)
    thread.start()

    tracker_ph = st.empty()
    st.markdown('<div class="log-title">Processing Log</div>', unsafe_allow_html=True)
    log_ph = st.empty()

    while thread.is_alive():
        log_text = "".join(log_lines)
        tracker_ph.markdown(render_stepper(steps, log_text), unsafe_allow_html=True)
        log_ph.code("\n".join(l.strip() for l in log_lines if l.strip()) or "Starting...", language="bash")
        time.sleep(0.15)
    thread.join()

    final_log = "".join(log_lines)
    tracker_ph.markdown(render_stepper(steps, final_log, done=True), unsafe_allow_html=True)
    log_ph.code("\n".join(l.strip() for l in log_lines if l.strip()), language="bash")

    if "error" in error_holder:
        raise error_holder["error"]
    return result_holder["value"], final_log


# ============================== SENDER ==============================
with tab_send:
    page_banner("blue", "📤", "Sender — Hide a Secret Image",
                "Pick a cover photo and the secret image you want to protect, add the receiver's "
                "public key, and the pipeline handles the quantum key, encryption, and GAN embedding.")

    step_heading("blue", "1", "Choose your images", "cover + secret")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            info_card_header("blue", "🖼️", "Cover Image", "The everyday photo that will hide your secret")
            cover_file = st.file_uploader("Cover Image", type=["png", "jpg", "jpeg"], key="cover",
                                           label_visibility="collapsed")
            if cover_file:
                st.image(cover_file, caption="Cover", use_container_width=True)
    with col2:
        with st.container(border=True):
            info_card_header("blue", "🕵️", "Secret Image", "The classified image you want to protect")
            secret_file = st.file_uploader("Secret Image", type=["png", "jpg", "jpeg"], key="secret",
                                            label_visibility="collapsed")
            if secret_file:
                st.image(secret_file, caption="Secret", use_container_width=True)

    st.write("")
    step_heading("blue", "2", "Add the receiver's key & run")

    with st.container(border=True):
        info_card_header("blue", "🔑", "Receiver's Public Key",
                          "Wraps the AES key so only the receiver can unlock it — a .pem file")
        pubkey_file = st.file_uploader("Receiver's Public Key (.pem)", type=["pem"], key="pubkey",
                                        label_visibility="collapsed")
        out_name = st.text_input("Output name", value="message", key="out_send")

    if st.button("🔐  Encrypt and Hide", type="primary", use_container_width=True):
        if not (cover_file and secret_file and pubkey_file):
            st.error("Cover image, secret image, and the receiver's public key are all required.")
        else:
            cover_path = save_uploaded_file(cover_file, UPLOAD_DIR, "cover_upload" + os.path.splitext(cover_file.name)[1])
            secret_path = save_uploaded_file(secret_file, UPLOAD_DIR, "secret_upload" + os.path.splitext(secret_file.name)[1])
            pubkey_path = save_uploaded_file(pubkey_file, UPLOAD_DIR, "pubkey_upload.pem")

            result, log_text = run_with_live_feedback(
                SEND_STEPS, send_module.send, cover_path, secret_path, pubkey_path, out_name or "message"
            )
            stego_path, enc_path, package_path, bundle_path, cover_resized_path = result

            st.success("✅  Secret hidden and encrypted successfully.")
            st.caption(f"Both images below are shown at the model's actual working "
                       f"resolution ({CFG.IMAGE_SIZE}x{CFG.IMAGE_SIZE}) for a fair comparison.")

            c1, c2 = st.columns(2)
            with c1:
                st.image(cover_resized_path, caption="Cover (as the model sees it)", width=350)
            with c2:
                st.image(stego_path, caption="Stego (secret hidden inside)", width=350)

            with open(bundle_path, "rb") as f:
                st.download_button(
                    "⬇️  Download Message File (.qsteg) — send this one file to the receiver",
                    data=f, file_name=os.path.basename(bundle_path),
                    mime="application/zip", use_container_width=True,
                )

# ============================== RECEIVER ==============================
with tab_receive:
    page_banner("green", "📥", "Receiver — Decrypt & Recover",
                "Generate your keypair once, share the public key with the sender, then drop in the "
                "message file and your private key to recover the original secret image.")

    step_heading("green", "1", "Your identity", "one-time setup — skip if already generated")

    with st.container(border=True):
        info_card_header("green", "🪪", "Generate Your Keypair",
                          "Creates your RSA public/private key pair for this session")
        if st.button("🔑  Generate My Keys"):
            os.makedirs(CFG.KEYS_DIR, exist_ok=True)
            priv, pub = generate_receiver_keypair(CFG.RSA_KEY_SIZE)
            priv_path = os.path.join(CFG.KEYS_DIR, "receiver_private_key.pem")
            pub_path = os.path.join(CFG.KEYS_DIR, "receiver_public_key.pem")
            serialize_private_key(priv, priv_path)
            serialize_public_key(pub, pub_path)
            st.success("✅  Keys generated.")
            c1, c2 = st.columns(2)
            with c1:
                with open(pub_path, "rb") as f:
                    st.download_button("⬇️  Download Public Key — share with sender", f,
                                        file_name="receiver_public_key.pem", use_container_width=True)
            with c2:
                with open(priv_path, "rb") as f:
                    st.download_button("⬇️  Download Private Key — keep confidential", f,
                                        file_name="receiver_private_key.pem", use_container_width=True)

    st.write("")
    step_heading("green", "2", "Decrypt and recover a message")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            info_card_header("green", "📦", "Message File", "The .qsteg bundle you received from the sender")
            message_file = st.file_uploader("Message File (.qsteg)", type=["qsteg"], key="msg",
                                             label_visibility="collapsed")
    with col2:
        with st.container(border=True):
            info_card_header("green", "🔐", "Your Private Key", "Keep this confidential — never share it")
            privkey_file = st.file_uploader("Your Private Key (.pem)", type=["pem"], key="privkey",
                                             label_visibility="collapsed")

    out_name_r = st.text_input("Output name", value="message", key="out_recv")

    if st.button("🔓  Decrypt and Recover", type="primary", use_container_width=True):
        if not (message_file and privkey_file):
            st.error("The message file (.qsteg) and your private key are both required.")
        else:
            msg_path = save_uploaded_file(message_file, UPLOAD_DIR, "message_upload.qsteg")
            privkey_path = save_uploaded_file(privkey_file, UPLOAD_DIR, "privkey_upload.pem")

            result, log_text = run_with_live_feedback(
                RECEIVE_STEPS, receive_module.receive, msg_path, privkey_path, out_name_r or "message"
            )
            exact_path, stego_recovered_path, *_ = result

            st.success("✅  Secret recovered successfully.")

            c1, c2 = st.columns(2)
            with c1:
                st.image(exact_path, caption="Exact Recovery (cryptographic — pixel-perfect)", width=350)
            with c2:
                st.image(stego_recovered_path, caption="Approximate Recovery (via GAN steganography)", width=350)

            match = re.search(r"PSNR:\s*([\d.]+)\s*dB\s*\|\s*SSIM:\s*([\d.]+)", log_text)
            if match:
                mcol1, mcol2 = st.columns(2)
                mcol1.metric("PSNR (Stego Recovery)", f"{match.group(1)} dB")
                mcol2.metric("SSIM (Stego Recovery)", match.group(2))

            dl1, dl2 = st.columns(2)
            with dl1:
                with open(exact_path, "rb") as f:
                    st.download_button("⬇️  Download Exact Recovery", f,
                                        file_name=os.path.basename(exact_path), use_container_width=True)
            with dl2:
                with open(stego_recovered_path, "rb") as f:
                    st.download_button("⬇️  Download Stego Recovery", f,
                                        file_name=os.path.basename(stego_recovered_path), use_container_width=True)

# ============================== ABOUT ==============================
with tab_about:
    page_banner("violet", "🧭", "How It Works",
                "A walk-through of the full pipeline, end to end — from the quantum key on the "
                "sender's side to the pixel-exact recovery on the receiver's side.")

    st.markdown(
        '<div class="scenario-banner">'
        '<span class="tag">Real-World Scenario</span>'
        '<p>A field operative needs to send a classified schematic to headquarters over an '
        'ordinary, unencrypted channel — email, a messaging app, a public photo upload — anything '
        'that could be intercepted. The image below looks like a holiday snapshot. It isn\u2019t. '
        'A cryptographically protected document is hidden inside it, and no observer, human or '
        'automated, can tell the difference.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- Stage 1: Sender assembles the message ----
    st.markdown(
        '<div class="stage-heading"><span class="stage-num">1</span>'
        '<h4>Sender prepares the payload</h4>'
        '<span class="stage-sub">&nbsp;&mdash; the Sender tab</span></div>',
        unsafe_allow_html=True,
    )
    s1c1, s1c2, s1c3 = st.columns(3)
    flow_card(s1c1, os.path.join(DEMO_ASSETS_DIR, "cover_demo.png"), "Cover Photo", "The decoy — an ordinary image")
    flow_card(s1c2, os.path.join(DEMO_ASSETS_DIR, "qubit_demo.png"), "Quantum Key", "Genuinely random via a qubit")
    flow_card(s1c3, os.path.join(DEMO_ASSETS_DIR, "secret_demo.png"), "Classified Document", "The real secret")

    st.write("")

    e1c1, e1c2, e1c3, e1c4, e1c5 = st.columns([3, 0.6, 3, 0.6, 3])
    flow_card(e1c1, os.path.join(DEMO_ASSETS_DIR, "encrypted_noise.png"), "Encrypted Payload", "AES-128 ciphertext")
    flow_badge(e1c2, "+")
    flow_card(e1c3, os.path.join(DEMO_ASSETS_DIR, "cover_demo.png"), "Cover Photo", "Unchanged input")
    flow_badge(e1c4, "=")
    flow_card(e1c5, os.path.join(DEMO_ASSETS_DIR, "stego_demo.png"), "Stego Image", "GAN-embedded output")

    st.markdown(
        '<div class="metric-pill-row">'
        '<span class="metric-pill">Encrypted before it\u2019s ever hidden</span>'
        '<span class="metric-pill">Quantum-random key material</span>'
        '<span class="metric-pill">Visually indistinguishable from the cover</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- Stage 2: Transmission ----
    st.markdown(
        '<div class="stage-heading"><span class="stage-num">2</span>'
        '<h4>Sent over an open channel</h4>'
        '<span class="stage-sub">&nbsp;&mdash; no encryption software required to move the file</span></div>',
        unsafe_allow_html=True,
    )
    t1, t2, t3 = st.columns([1, 2, 1])
    flow_card(t2, os.path.join(DEMO_ASSETS_DIR, "stego_demo.png"), "What an interceptor sees", "Just another photo")

    # ---- Stage 3: Receiver recovers the secret ----
    st.markdown(
        '<div class="stage-heading receiver"><span class="stage-num">3</span>'
        '<h4>Receiver extracts the secret</h4>'
        '<span class="stage-sub">&nbsp;&mdash; the Receiver tab</span></div>',
        unsafe_allow_html=True,
    )
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns([3, 0.6, 3, 0.6, 3])
    flow_card(r2c1, os.path.join(DEMO_ASSETS_DIR, "stego_demo.png"), "Stego Image Received", "From the open channel")
    flow_badge(r2c2, "\u2192", green=True)
    flow_card(r2c3, os.path.join(DEMO_ASSETS_DIR, "diff_heatmap.png"), "Difference vs. Cover", "Amplified 40\u00d7 \u2014 proof it's imperceptible")
    flow_badge(r2c4, "\u2192", green=True)
    flow_card(r2c5, os.path.join(DEMO_ASSETS_DIR, "recovered_demo.png"), "Recovered Document", "Decoded + decrypted \u2014 pixel-exact")

    st.write("")

    st.markdown(
        '<div class="guarantee-row">'
        '<div class="guarantee-card a"><h5>&#128065;&#65039;&#8205;&#128488;&#65039; Concealment (Steganography)</h5>'
        '<p>A bystander who intercepts the photo cannot tell a hidden message exists at all \u2014 '
        'the GAN encoder is trained adversarially against a discriminator until the stego image '
        'is statistically indistinguishable from the cover.</p></div>'
        '<div class="guarantee-card b"><h5>&#128272; Confidentiality (Cryptography)</h5>'
        '<p>Even if someone suspects a hidden payload and extracts it, it remains unreadable '
        'without the receiver\u2019s private key \u2014 the AES key itself is quantum-random and '
        'RSA-wrapped, and the private key never travels over the network.</p></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Full technical pipeline \u2014 all 6 steps"):
        st.markdown("""
1. **Quantum-assisted key generation** — a qubit is put into superposition (Hadamard gate)
   and measured; genuinely random by the laws of quantum physics (via IBM Qiskit,
   falls back to a classical secure RNG if Qiskit/hardware is unavailable).
2. **RSA key exchange** — the receiver's public key wraps the AES key; only the
   receiver's private key, which never travels over the network, can unwrap it.
3. **AES-128 (CTR) encryption** — the real secret image is encrypted, byte-exact
   and fully reversible with the correct key.
4. **GAN steganographic embedding** — a CNN encoder hides the real secret image
   inside the cover as a small residual, trained adversarially against a
   discriminator that tries to distinguish cover images from stego images.
5. **GAN decoding** — a CNN decoder extracts an approximate copy of the hidden
   secret from the stego image, measured with PSNR and SSIM.
6. **AES decryption** — the encrypted companion file is decrypted with the
   unwrapped key to produce an exact, pixel-perfect copy of the original secret.
        """)

    st.markdown(
        '<div class="skills-strip">'
        '<div class="skills-title">Techniques demonstrated in this project</div>'
        '<div class="tech-badge-row">'
        '<div class="tech-badge"><b>Quantum Computing</b>IBM Qiskit \u2014 Hadamard gate superposition for true random key bits</div>'
        '<div class="tech-badge"><b>Public-Key Cryptography</b>RSA-2048 key exchange, no shared secret ever transmitted</div>'
        '<div class="tech-badge"><b>Symmetric Encryption</b>AES-128 in CTR mode for byte-exact, reversible encryption</div>'
        '<div class="tech-badge"><b>Deep Learning</b>Adversarially trained GAN encoder/decoder (PyTorch) for steganography</div>'
        '<div class="tech-badge"><b>Full-Stack Delivery</b>Streamlit UI, live background processing, packaged deployable app</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )