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

/* ---- Landing page ---- */
.landing-spacer { height: 16vh; }
.hero-title.landing { padding: 4.2rem 2.5rem 4rem 2.5rem; max-width: 1000px; margin: 0 auto 2.2rem auto; gap: 1.6rem; border-radius: 28px; }
.hero-title.landing .hero-icon-badge { width: 92px; height: 92px; border-radius: 26px; }
.hero-title.landing .hero-icon-badge svg { width: 50px; height: 50px; }
.hero-title.landing .hero-top { flex-direction: column; gap: 1.6rem; }
.hero-title.landing h1 { font-size: 3.3rem; max-width: 860px; }

/* ---- Sidebar navigation ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(185deg, #0a1130 0%, #111a4a 55%, #1a1f5c 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
    width: 300px !important; min-width: 300px !important;
}
section[data-testid="stSidebar"] > div { padding-top: 0.4rem; }
/* kill the generic card styling inside the sidebar (it caused the white box + faded text) */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"],
section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}
.side-brand { display: flex; align-items: center; gap: 0.85rem; padding: 0.6rem 0.2rem 1.3rem 0.2rem; margin-bottom: 1.4rem; border-bottom: 1px solid rgba(255,255,255,0.10); }
.side-brand .badge { width: 46px; height: 46px; border-radius: 14px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 1.35rem;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6); box-shadow: 0 8px 20px rgba(99,102,241,0.45); }
.side-brand .name { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.08rem; line-height: 1.2; color: #ffffff; }
.side-brand .sub { font-size: 0.74rem; font-weight: 600; letter-spacing: 0.08em; color: #8fa0e0; margin-top: 3px; }
.side-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.16em; color: #7f8fd6; margin: 0 0 0.7rem 0.4rem; }
.side-divider { height: 1px; background: rgba(255,255,255,0.10); margin: 1.4rem 0 1.1rem 0; }
section[data-testid="stSidebar"] .stButton { margin-bottom: 0.35rem; }
section[data-testid="stSidebar"] .stButton button {
    justify-content: flex-start !important; text-align: left !important; min-height: 3.1rem;
    padding: 0.7rem 1.1rem !important; border-radius: 12px !important; box-shadow: none !important; transition: all 0.18s ease !important;
}
section[data-testid="stSidebar"] .stButton button p { font-size: 1.02rem !important; font-weight: 600 !important; }
section[data-testid="stSidebar"] .stButton button[kind="secondary"],
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-secondary"] {
    background: transparent !important; border: 1.5px solid transparent !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"] p,
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-secondary"] p { color: #d4dcff !important; }
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover,
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-secondary"]:hover {
    background: rgba(255,255,255,0.09) !important; border-color: rgba(255,255,255,0.14) !important; transform: translateX(4px);
}
section[data-testid="stSidebar"] .stButton button[kind="primary"],
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(120deg, #3b82f6 0%, #7c4dd6 100%) !important; border: none !important;
    box-shadow: 0 8px 22px rgba(79,70,229,0.5) !important;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"] p,
section[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] p { color: #ffffff !important; }
.side-foot { margin-top: 1.4rem; padding: 0.9rem 1rem; border-radius: 12px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); }
.side-foot .t { font-size: 0.82rem; font-weight: 700; color: #7ee7b3; }
.side-foot .d { font-size: 0.76rem; color: #9fb0ea; margin-top: 3px; line-height: 1.5; }

/* ================= Polish pass ================= */
/* button text colours (were inheriting dark body text) */
.stButton button[kind="primary"] p, .stButton button[data-testid="stBaseButton-primary"] p { color: #ffffff !important; }
.stButton button[kind="secondary"] p, .stButton button[data-testid="stBaseButton-secondary"] p { color: var(--sender) !important; }
.stDownloadButton button p, .stDownloadButton button span { color: var(--receiver) !important; font-weight: 700 !important; }

/* light file chips instead of black */
[data-testid="stFileUploaderFile"], div[class*="uploadedFile"] {
    background: var(--sender-soft) !important; border: 1.5px solid var(--sender-mid) !important; border-radius: 10px !important;
}
[data-testid="stFileUploaderFile"] *, div[class*="uploadedFile"] * { color: var(--ink) !important; opacity: 1 !important; }
[data-testid="stFileUploaderFileName"] { color: var(--ink) !important; font-weight: 600 !important; }
[data-testid="stFileUploaderFile"] small, div[class*="uploadedFile"] small { color: var(--muted) !important; }
[data-testid="stFileUploaderDeleteBtn"] svg { fill: var(--ink) !important; }

/* text input: no black border */
.stTextInput div[data-baseweb="input"] {
    background: #ffffff !important; border: 1.5px solid var(--border) !important; border-radius: 10px !important; box-shadow: none !important;
}
.stTextInput div[data-baseweb="input"]:focus-within { border-color: var(--sender) !important; box-shadow: 0 0 0 3px var(--sender-soft) !important; }
.stTextInput input { border: none !important; box-shadow: none !important; background: transparent !important; color: var(--ink) !important; }

/* images centred inside cards */
[data-testid="stImage"] { display: flex; flex-direction: column; align-items: center; }
[data-testid="stImageCaption"] { text-align: center !important; color: var(--muted) !important; }

/* page workflow strip */
.page-steps { display: flex; gap: 0.9rem; margin: 0 0 1.8rem 0; }
.page-steps .ps { flex: 1; display: flex; align-items: center; gap: 0.75rem; background: #ffffff; border: 1.5px solid var(--border); border-radius: 12px; padding: 0.75rem 1rem; }
.page-steps .ps .n { width: 30px; height: 30px; border-radius: 50%; background: var(--sender); color: #ffffff; font-weight: 700; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.page-steps.green .ps .n { background: var(--receiver); }
.page-steps .ps .t { font-weight: 600; color: var(--ink); font-size: 0.96rem; line-height: 1.3; }

/* ================= Landing page ================= */
.lp-hero {
    position: relative; overflow: hidden; min-height: 66vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
    padding: 4rem 1.5rem; border-radius: 32px;
    background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,255,255,0.45));
    border: 1.5px solid var(--sender-mid); box-shadow: 0 24px 60px rgba(47,93,212,0.14);
    opacity: 0; animation: dropIn 0.6s ease-out forwards;
}
.lp-hero .hero-icon-badge {
    width: 92px; height: 92px; border-radius: 26px; display: flex; align-items: center; justify-content: center; position: relative;
    background: linear-gradient(135deg, var(--sender), var(--quantum));
    box-shadow: 0 12px 28px rgba(124,77,214,0.38), 0 0 0 9px rgba(124,77,214,0.08);
}
.lp-hero .hero-icon-badge svg { width: 50px; height: 50px; }
.lp-orbits { position: absolute; left: 50%; top: 50%; width: min(1050px, 98%); transform: translate(-50%, -50%); pointer-events: none; }
.lp-eyebrow {
    position: relative; margin: 1.6rem 0 1rem 0; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.18em; color: var(--quantum);
    background: var(--quantum-soft); border: 1.5px solid var(--quantum-mid); border-radius: 30px; padding: 0.4rem 1.1rem;
}
.lp-hero h1 {
    position: relative; margin: 0; max-width: 980px; font-size: clamp(2.6rem, 5.2vw, 4.5rem); font-weight: 800; line-height: 1.1; letter-spacing: -0.025em;
    background: linear-gradient(100deg, var(--sender) 0%, var(--quantum) 55%, var(--receiver) 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; color: var(--ink);
}
.lp-tag { position: relative; margin: 1.5rem 0 0 0; max-width: 760px; font-size: 1.22rem; font-weight: 500; color: var(--ink) !important; line-height: 1.65; }
.lp-sub { position: relative; margin: 0.7rem 0 0 0; max-width: 700px; font-size: 1.04rem; color: var(--body) !important; line-height: 1.65; }
.lp-pills { position: relative; display: flex; flex-wrap: wrap; justify-content: center; gap: 0.7rem; margin-top: 1.8rem; }
.lp-pills span { font-size: 0.92rem; font-weight: 700; color: var(--receiver); background: var(--receiver-soft); border: 1.5px solid var(--receiver-mid); border-radius: 30px; padding: 0.42rem 1rem; }
.lp-chip {
    position: absolute; font-size: 0.92rem; font-weight: 700; color: var(--ink); background: rgba(255,255,255,0.85);
    border: 1.5px solid var(--border); border-radius: 14px; padding: 0.6rem 1rem; box-shadow: 0 10px 24px rgba(16,22,43,0.10);
    animation: lpFloat 6s ease-in-out infinite;
}
.lp-chip.c1 { top: 12%; left: 4%; } .lp-chip.c2 { top: 20%; right: 4%; animation-delay: 1.2s; }
.lp-chip.c3 { bottom: 18%; left: 6%; animation-delay: 2.1s; } .lp-chip.c4 { bottom: 12%; right: 5%; animation-delay: 0.6s; }
@keyframes lpFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
@media (max-width: 1100px) { .lp-chip { display: none; } }

.lp-hint { text-align: center; font-size: 0.92rem; color: var(--muted) !important; margin-top: 0.6rem; }
.lp-section-title { text-align: center; font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; color: var(--ink); margin: 3.2rem 0 0.4rem 0; }
.lp-section-sub { text-align: center; color: var(--body) !important; margin: 0 0 1.6rem 0; }
.lp-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.1rem; }
.lp-card { background: rgba(255,255,255,0.85); border: 1.5px solid var(--border); border-radius: 18px; padding: 1.5rem 1.4rem; transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; }
.lp-card:hover { transform: translateY(-5px); box-shadow: 0 16px 32px rgba(16,22,43,0.10); border-color: var(--quantum); }
.lp-card .ic { width: 54px; height: 54px; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 1rem; }
.lp-card.a .ic { background: var(--quantum-soft); } .lp-card.b .ic { background: var(--sender-soft); }
.lp-card.c .ic { background: var(--receiver-soft); } .lp-card.d .ic { background: #fdf3dc; }
.lp-card h4 { margin: 0 0 0.45rem 0; font-size: 1.15rem; font-weight: 700; color: var(--ink) !important; }
.lp-card p { margin: 0; font-size: 0.95rem; color: var(--body) !important; line-height: 1.6; }
.lp-flow { display: flex; align-items: stretch; gap: 0.9rem; }
.lp-flow .st { flex: 1; background: rgba(255,255,255,0.85); border: 1.5px solid var(--border); border-radius: 18px; padding: 1.4rem 1.5rem; text-align: center; }
.lp-flow .st .n { font-size: 2rem; }
.lp-flow .st h5 { margin: 0.5rem 0 0.35rem 0; font-size: 1.1rem; font-weight: 700; color: var(--ink) !important; }
.lp-flow .st p { margin: 0; font-size: 0.92rem; color: var(--body) !important; line-height: 1.55; }
.lp-flow .st.s { border-color: var(--sender-mid); background: linear-gradient(160deg, var(--sender-soft), #ffffff); }
.lp-flow .st.r { border-color: var(--receiver-mid); background: linear-gradient(160deg, var(--receiver-soft), #ffffff); }
.lp-flow .ar { display: flex; align-items: center; font-size: 1.8rem; color: var(--quantum); font-weight: 700; }
.lp-foot { text-align: center; color: var(--muted) !important; font-size: 0.88rem; margin: 3rem 0 0.5rem 0; }
@media (max-width: 900px) { .lp-grid { grid-template-columns: repeat(2, 1fr); } .lp-flow { flex-direction: column; } .lp-flow .ar { justify-content: center; transform: rotate(90deg); } }

/* ================= Final polish ================= */
/* 1) Stop column wrappers + the page container from being drawn as cards (caused double borders / big white panel) */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="column"] > div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover,
div[data-testid="column"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.page-banner),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.page-banner):hover {
    background: transparent !important; border: none !important; box-shadow: none !important;
    padding: 0 !important; margin: 0 !important; border-radius: 0 !important;
}
/* 2) Capability chips on the Demo Steps page */
.capability-strip { display: flex; flex-wrap: wrap; gap: 0.6rem; margin: 0 0 1.5rem 0; }
.capability-strip span { font-size: 0.88rem; font-weight: 700; color: var(--quantum); background: var(--quantum-soft);
    border: 1.5px solid var(--quantum-mid); border-radius: 30px; padding: 0.42rem 1.05rem; }
/* 3) Inputs: white background, hide Deploy button */
.stTextInput [data-baseweb="base-input"] { background: #ffffff !important; }
[data-testid="stAppDeployButton"], .stDeployButton { display: none !important; }

/* ===== text input: always white, even when the browser/Streamlit is in dark mode ===== */
[data-testid="stTextInput"] [data-baseweb="input"], [data-testid="stTextInput"] [data-baseweb="base-input"],
[data-testid="stTextInputRootElement"], .stTextInput [data-baseweb="input"], .stTextInput [data-baseweb="base-input"] {
    background: #ffffff !important; background-color: #ffffff !important;
}
[data-testid="stTextInput"] [data-baseweb="input"], .stTextInput [data-baseweb="input"] {
    border: 1.5px solid var(--border) !important; border-radius: 10px !important; box-shadow: none !important;
}
[data-testid="stTextInput"] input, .stTextInput input {
    background: #ffffff !important; color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; caret-color: var(--sender);
}
[data-testid="stTextInput"] input::placeholder, .stTextInput input::placeholder { color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; }

/* ================= Page banners: dark artwork header (matches the cover) ================= */
.page-banner {
    position: relative; overflow: hidden; min-height: 150px; padding: 1.8rem 2.1rem !important; gap: 1.3rem !important;
    background-color: #050d1f !important; background-image: linear-gradient(120deg, #050d1f 0%, #0b1d3a 100%) !important;
    background-size: cover !important; background-position: 70% 55% !important;
    border: 1px solid rgba(103,232,249,0.30) !important; box-shadow: 0 12px 30px rgba(3,10,20,0.28);
}
.page-banner::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px; background: linear-gradient(90deg, var(--acc, #22d3ee) 0%, transparent 70%); }
.page-banner .emoji {
    width: 64px; height: 64px; border-radius: 18px; display: flex; align-items: center; justify-content: center; font-size: 2rem !important;
    background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.28); backdrop-filter: blur(4px); flex-shrink: 0;
}
.page-banner h2, .page-banner.blue h2, .page-banner.green h2, .page-banner.violet h2 { color: #ffffff !important; font-size: 2rem !important; text-shadow: 0 0 22px var(--acc, #22d3ee); }
.page-banner p { color: #d5e3ed !important; max-width: 760px !important; }
.page-banner.blue   { --acc: #60a5fa; border-color: rgba(96,165,250,0.55) !important; }
.page-banner.green  { --acc: #34d399; border-color: rgba(52,211,153,0.55) !important; }
.page-banner.violet { --acc: #a78bfa; border-color: rgba(167,139,250,0.55) !important; }
</style>
""", unsafe_allow_html=True)

# ============================== SESSION STATE ==============================
if "stage" not in st.session_state:
    st.session_state.stage = "cover"   # cover -> intro -> app
if "page" not in st.session_state:
    st.session_state.page = "Sender"

HERO_ICON = """
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
"""

# ============================== PAGE 1 & 2: COVER + OVERVIEW ==============================
def _cover_bg_uri():
    """Dark circuit-board backdrop: green/purple edge glows, data panels, traces, pixel blocks."""
    import random, urllib.parse
    rnd = random.Random(21)
    W, H = 1600, 900
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">']
    s.append('<defs>'
             '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#030b16"/><stop offset="1" stop-color="#06182a"/></linearGradient>'
             '<radialGradient id="gl" cx="0%" cy="62%" r="42%"><stop offset="0" stop-color="#10b981" stop-opacity="0.42"/><stop offset="1" stop-color="#10b981" stop-opacity="0"/></radialGradient>'
             '<radialGradient id="gr" cx="100%" cy="30%" r="46%"><stop offset="0" stop-color="#7c3aed" stop-opacity="0.40"/><stop offset="1" stop-color="#7c3aed" stop-opacity="0"/></radialGradient>'
             '<radialGradient id="gc" cx="50%" cy="64%" r="38%"><stop offset="0" stop-color="#0891b2" stop-opacity="0.30"/><stop offset="1" stop-color="#0891b2" stop-opacity="0"/></radialGradient>'
             '</defs>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#gl)"/><rect width="{W}" height="{H}" fill="url(#gr)"/><rect width="{W}" height="{H}" fill="url(#gc)"/>')
    for x in range(0, W, 70):
        s.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#22d3ee" stroke-opacity="0.03"/>')
    for y in range(0, H, 70):
        s.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#22d3ee" stroke-opacity="0.03"/>')
    # translucent "data panels" on both sides
    panels = [(110, 430, 190, 120), (40, 580, 130, 90), (250, 610, 170, 70), (30, 290, 110, 100),
              (1270, 250, 210, 130), (1390, 430, 170, 110), (1220, 570, 160, 100), (1470, 150, 100, 90)]
    for (x, y, w, h) in panels:
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#5eead4" fill-opacity="0.05" stroke="#22d3ee" stroke-opacity="0.16"/>')
        for k in range(4):
            lw = rnd.randint(int(w * 0.25), int(w * 0.8))
            s.append(f'<rect x="{x + 12}" y="{y + 16 + k * 14}" width="{lw}" height="4" rx="2" fill="#67e8f9" fill-opacity="{rnd.uniform(0.10, 0.28):.2f}"/>')
    # circuit traces coming in from both edges
    for side in (0, 1):
        for _ in range(9):
            y0 = rnd.randint(40, H - 40)
            x0 = -10 if side == 0 else W + 10
            d = 1 if side == 0 else -1
            l1, l2 = rnd.randint(90, 220), rnd.randint(60, 200)
            dy = rnd.choice([-1, 1]) * rnd.randint(30, 90)
            pts = [(x0, y0), (x0 + d * l1, y0), (x0 + d * (l1 + abs(dy)), y0 + dy), (x0 + d * (l1 + abs(dy) + l2), y0 + dy)]
            s.append('<polyline points="' + " ".join(f"{px},{py}" for px, py in pts) + '" fill="none" stroke="#22d3ee" stroke-opacity="0.22" stroke-width="1.6"/>')
            ex, ey = pts[-1]
            s.append(f'<circle cx="{ex}" cy="{ey}" r="4" fill="#67e8f9" fill-opacity="0.85"/><circle cx="{ex}" cy="{ey}" r="11" fill="#22d3ee" fill-opacity="0.14"/>')
    # pixel blocks + glow dots (kept away from the centre so text stays readable)
    for _ in range(70):
        side = rnd.random() < 0.5
        x = rnd.randint(10, 520) if side else rnd.randint(W - 520, W - 10)
        y = rnd.randint(20, H - 20)
        z = rnd.randint(7, 20)
        col = rnd.choice(["#2dd4bf", "#a78bfa", "#22d3ee", "#34d399"])
        s.append(f'<rect x="{x}" y="{y}" width="{z}" height="{z}" rx="2" fill="{col}" fill-opacity="{rnd.uniform(0.10, 0.32):.2f}"/>')
    for _ in range(26):
        x, y = rnd.randint(10, W - 10), rnd.randint(10, H - 10)
        if 560 < x < 1040 and 120 < y < 760:
            continue
        s.append(f'<circle cx="{x}" cy="{y}" r="2.4" fill="#67e8f9"/><circle cx="{x}" cy="{y}" r="8" fill="#22d3ee" fill-opacity="0.15"/>')
    s.append('</svg>')
    return "data:image/svg+xml," + urllib.parse.quote("".join(s), safe="")


@st.cache_data(show_spinner=False)
def _cover_photo_uri():
    """Cover artwork shipped next to this file (cover_bg.jpg), embedded as a data-URI."""
    import base64
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover_bg.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    return None


def _bg_uri():
    # falls back to the generated SVG backdrop if cover_bg.jpg is missing
    return _cover_photo_uri() or _cover_bg_uri()


@st.cache_data(show_spinner=False)
def _banner_photo_uri():
    """Slim crop of the cover artwork (banner_bg.jpg next to this file) used behind each page title."""
    import base64
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banner_bg.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    return None


def _ico(kind):
    """Small neon line icons (48x48) used on the overview page."""
    base = '<svg viewBox="0 0 48 48" fill="none" stroke="#67e8f9" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">'
    body = {
        "atom": '<ellipse cx="24" cy="24" rx="19" ry="7.5"/><ellipse cx="24" cy="24" rx="19" ry="7.5" transform="rotate(60 24 24)"/><ellipse cx="24" cy="24" rx="19" ry="7.5" transform="rotate(120 24 24)"/><circle cx="24" cy="24" r="3" fill="#67e8f9"/>',
        "key": '<circle cx="15" cy="24" r="8"/><path d="M23 24h19M36 24v7M42 24v5"/>',
        "lock": '<rect x="11" y="22" width="26" height="18" rx="4"/><path d="M16 22v-6a8 8 0 0 1 16 0v6"/><circle cx="24" cy="31" r="2.5" fill="#67e8f9"/>',
        "net": '<circle cx="9" cy="24" r="4"/><circle cx="24" cy="9" r="4"/><circle cx="24" cy="39" r="4"/><circle cx="39" cy="24" r="4"/><circle cx="24" cy="24" r="3" fill="#67e8f9"/><path d="M12.5 21.5L21 11M12.5 26.5L21 37M27 11l9 10M27 37l9-10M24 13v8M24 27v8"/>',
        "up": '<rect x="8" y="20" width="32" height="22" rx="4"/><path d="M24 15V4M18 9l6-6 6 6M12 36l8-8 5 5 5-6 6 9"/>',
        "globe": '<circle cx="24" cy="24" r="17"/><ellipse cx="24" cy="24" rx="7" ry="17"/><path d="M7 24h34M10 14h28M10 34h28"/>',
        "down": '<rect x="8" y="6" width="32" height="22" rx="4"/><path d="M24 33v11M18 39l6 6 6-6M12 22l8-8 5 5 5-6 6 9"/>',
    }[kind]
    return base + body + '</svg>'


_BASE_INTRO_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800;900&display=swap');
section[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}
/* neon CTA buttons */
.stApp .stButton button[kind="primary"], .stApp .stButton button[data-testid="stBaseButton-primary"] {
    padding: 0.95rem 1.4rem !important; border-radius: 14px !important;
    background: linear-gradient(180deg, #3ee6fb 0%, #0fb7d8 100%) !important; border: 1px solid #9af3ff !important;
    box-shadow: 0 0 0 4px rgba(34,211,238,0.14), 0 0 34px rgba(34,211,238,0.6) !important;
}
.stApp .stButton button[kind="primary"] p, .stApp .stButton button[data-testid="stBaseButton-primary"] p {
    color: #03222e !important; font-size: 1.08rem !important; font-weight: 800 !important; letter-spacing: 0.12em !important; text-transform: uppercase;
}
.stApp .stButton button[kind="primary"]:hover { transform: translateY(-3px); box-shadow: 0 0 0 5px rgba(34,211,238,0.2), 0 0 46px rgba(34,211,238,0.85) !important; }
.stApp .stButton button[kind="secondary"], .stApp .stButton button[data-testid="stBaseButton-secondary"] {
    padding: 0.95rem 1.4rem !important; border-radius: 14px !important; background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(160,230,245,0.45) !important;
}
.stApp .stButton button[kind="secondary"] p, .stApp .stButton button[data-testid="stBaseButton-secondary"] p {
    color: #cfeaf4 !important; font-size: 1.02rem !important; font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase;
}
.stApp .stButton button[kind="secondary"]:hover { background: rgba(34,211,238,0.12) !important; border-color: #67e8f9 !important; }
.block-container { max-width: 100% !important; padding: 0 2rem 1rem 2rem !important; }
@keyframes cv2dash { to { stroke-dashoffset: -24; } }
@keyframes cv2float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@keyframes cv2pulse { 0%,100% { stroke-opacity: 1; } 50% { stroke-opacity: 0.55; } }
@keyframes cv2bits { 0% { opacity: 0.15; } 50% { opacity: 0.95; } 100% { opacity: 0.15; } }
.cv2-stream { stroke-dasharray: 5 7; animation: cv2dash 0.9s linear infinite; }
.cv2-float { animation: cv2float 5s ease-in-out infinite; }
.cv2-pulse { animation: cv2pulse 3s ease-in-out infinite; }
.cv2-bits { animation: cv2bits 2.4s ease-in-out infinite; }
"""

COVER_CSS = """<style>""" + _BASE_INTRO_CSS + """
.stApp {
    background-color: #030b16 !important;
    background-image: linear-gradient(180deg, rgba(3,10,20,0.62) 0%, rgba(3,10,20,0) 42%), url("{{BG}}") !important;
    background-size: cover, cover !important; background-position: center, center 72% !important;
    background-repeat: no-repeat, no-repeat !important; background-attachment: fixed, fixed !important;
}
.cv3 { display: flex; flex-direction: column; align-items: center; text-align: center; padding-top: 5.5vh; font-family: 'Montserrat', 'Space Grotesk', sans-serif; }
h1.cv3-title {
    margin: 0; font-family: 'Montserrat', 'Space Grotesk', sans-serif; font-weight: 800; text-transform: uppercase;
    font-size: min(3.3vw, 6.6vh); line-height: 1.12; letter-spacing: 0.015em;
    background: linear-gradient(180deg, #f0feff 0%, #7cf0ff 45%, #2bd9f0 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 14px rgba(34,211,238,0.6)) drop-shadow(0 0 32px rgba(34,211,238,0.25));
}
p.cv3-desc { margin: 2vh 0 0 0; max-width: min(48vw, 760px); font-size: min(1.3vw, 2.5vh); font-weight: 500; line-height: 1.5; color: #f1f7fb !important; }
.cv3-tags { display: flex; gap: 1.1rem; margin-top: 2.6vh; }
.cv3-tags span { font-size: min(0.82vw, 1.6vh); font-size: max(0.78rem, min(0.82vw, 1.6vh)); font-weight: 600; letter-spacing: 0.06em; border-radius: 6px; padding: 0.5rem 1.4rem; }
.cv3-tags .a { color: #e8fdff; background: rgba(34,211,238,0.5); border: 1px solid #7cf0ff; box-shadow: 0 0 18px rgba(34,211,238,0.55); }
.cv3-tags .b { color: #9ff3cf; background: rgba(16,185,129,0.14); border: 1px solid rgba(52,211,153,0.75); box-shadow: 0 0 16px rgba(16,185,129,0.35); }
/* pin the (only) column row -- i.e. the Get Started button -- near the bottom, centred */
div[data-testid="stHorizontalBlock"] { position: fixed !important; bottom: 7vh; left: 0; right: 0; z-index: 50; }
</style>"""

COVER_HTML = """<div class="cv3">
<h1 class="cv3-title">Quantum Key Driven Image<br/>Steganography &amp; Steganalysis</h1>
<p class="cv3-desc">Hide a classified image inside an ordinary photo — protected end-to-end by a quantum-random key, RSA, AES and an adversarial GAN.</p>
<div class="cv3-tags"><span class="a">EMBED DATA</span><span class="b">DETECT HIDDEN DATA</span></div>
</div>"""

INTRO_CSS = """<style>""" + _BASE_INTRO_CSS + """
.block-container { max-width: 1240px !important; padding: 1.4rem 2rem 2rem 2rem !important; }
.stApp {
    background-color: #030b16 !important;
    background-image: linear-gradient(rgba(3,11,22,0.80), rgba(3,11,22,0.80)), url("{{BG}}") !important;
    background-size: cover, cover !important; background-position: center, center !important; background-attachment: fixed, fixed !important;
}
.in2 { font-family: 'Montserrat', 'Space Grotesk', sans-serif; }
.in2-top { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.2rem; }
.in2-top .tag { font-size: 0.78rem; font-weight: 800; letter-spacing: 0.2em; color: #67e8f9; background: rgba(34,211,238,0.12);
    border: 1px solid rgba(34,211,238,0.55); border-radius: 8px; padding: 0.4rem 0.9rem; }
.in2-top .nm { font-size: 0.95rem; font-weight: 700; color: #cfeaf4; }
h2.in2-h { margin: 1.6rem 0 0.3rem 0; text-align: center; font-family: 'Montserrat', 'Space Grotesk', sans-serif; font-size: 2.1rem; font-weight: 800;
    color: #ffffff !important; text-shadow: 0 0 22px rgba(34,211,238,0.45); }
p.in2-sub { text-align: center; margin: 0 0 1.4rem 0; font-size: 1.02rem; color: #a9c4d2 !important; }
.in2-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.1rem; }
.in2-card { position: relative; overflow: hidden; border-radius: 18px; padding: 1.4rem 1.3rem 1.3rem 1.3rem;
    background: linear-gradient(165deg, rgba(16,48,78,0.78), rgba(7,22,40,0.82)); border: 1px solid rgba(103,232,249,0.26);
    box-shadow: 0 10px 30px rgba(0,0,0,0.35); transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
.in2-card:hover { transform: translateY(-5px); border-color: #67e8f9; box-shadow: 0 14px 36px rgba(34,211,238,0.22); }
.in2-card::before { content: ""; position: absolute; left: 0; top: 0; right: 0; height: 3px; background: linear-gradient(90deg, #22d3ee, #8b5cf6, #34d399); }
.in2-card .num { position: absolute; top: 0.9rem; right: 1.1rem; font-size: 1.6rem; font-weight: 900; color: rgba(103,232,249,0.18); }
.in2-card .ic { width: 58px; height: 58px; border-radius: 16px; display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;
    background: rgba(34,211,238,0.10); border: 1px solid rgba(34,211,238,0.4); box-shadow: 0 0 18px rgba(34,211,238,0.25); }
.in2-card .ic svg { width: 32px; height: 32px; }
.in2-card h4 { margin: 0 0 0.45rem 0; font-size: 1.08rem; font-weight: 700; color: #ffffff !important; }
.in2-card p { margin: 0; font-size: 0.9rem; line-height: 1.6; color: #a9c4d2 !important; }
.in2-flow { display: flex; align-items: stretch; gap: 0.5rem; }
.in2-node { flex: 1; text-align: center; border-radius: 18px; padding: 1.2rem 1.2rem; background: linear-gradient(165deg, rgba(16,48,78,0.70), rgba(7,22,40,0.80)); border: 1px solid rgba(103,232,249,0.22); }
.in2-node.s { border-color: rgba(96,165,250,0.6); box-shadow: 0 0 24px rgba(59,130,246,0.22); }
.in2-node.r { border-color: rgba(52,211,153,0.6); box-shadow: 0 0 24px rgba(16,185,129,0.22); }
.in2-node .ic { width: 54px; height: 54px; margin: 0 auto 0.6rem auto; }
.in2-node .ic svg { width: 100%; height: 100%; }
.in2-node.r .ic svg { stroke: #6ee7b7; }
.in2-node h5 { margin: 0 0 0.3rem 0; font-size: 1.05rem; font-weight: 700; color: #ffffff !important; }
.in2-node p { margin: 0; font-size: 0.88rem; line-height: 1.55; color: #a9c4d2 !important; }
.in2-conn { width: 90px; flex-shrink: 0; display: flex; align-items: center; }
.in2-conn svg { width: 100%; height: 20px; overflow: visible; }
.in2-gap { height: 1.6rem; }
@media (max-width: 900px) { .in2-grid { grid-template-columns: repeat(2, 1fr); } .in2-flow { flex-direction: column; } .in2-conn { display: none; } }
</style>"""

_CONN = '<div class="in2-conn"><svg viewBox="0 0 90 20" xmlns="http://www.w3.org/2000/svg"><line class="cv2-stream" x1="2" y1="10" x2="80" y2="10" stroke="#22d3ee" stroke-width="2.4"/><polygon points="78,4 90,10 78,16" fill="#22d3ee"/></svg></div>'


def _intro_html():
    cards = [
        ("01", "atom", "Quantum Key Generation", "A qubit in superposition produces genuinely random key bits for the AES key (IBM Qiskit)."),
        ("02", "key", "RSA-2048 Key Exchange", "The receiver's public key wraps the AES key. The private key never travels over the network."),
        ("03", "lock", "AES-128 Encryption", "The secret image is encrypted byte-exact in CTR mode before it is ever hidden."),
        ("04", "net", "GAN Steganography", "An adversarially trained encoder hides the payload inside the cover so it stays invisible."),
    ]
    grid = "".join(f'<div class="in2-card"><div class="num">{n}</div><div class="ic">{_ico(i)}</div><h4>{t}</h4><p>{d}</p></div>' for n, i, t, d in cards)
    flow = (
        f'<div class="in2-node s"><div class="ic">{_ico("up")}</div><h5>Sender hides</h5><p>Picks a cover photo and a secret image, adds the receiver\'s public key.</p></div>'
        + _CONN +
        f'<div class="in2-node"><div class="ic">{_ico("globe")}</div><h5>Open channel</h5><p>The stego image travels like any ordinary photo. Nothing looks suspicious.</p></div>'
        + _CONN +
        f'<div class="in2-node r"><div class="ic">{_ico("down")}</div><h5>Receiver recovers</h5><p>Uses the private key to decrypt and recover the original secret image.</p></div>'
    )
    return (
        '<div class="in2">'
        '<div class="in2-top"><span class="tag">STEP 2 OF 3 · OVERVIEW</span><span class="nm">Quantum Key Driven Image Steganography &amp; Steganalysis</span></div>'
        '<h2 class="in2-h">What powers the pipeline</h2>'
        '<p class="in2-sub">Four layers of protection working together, from key generation to hiding the data.</p>'
        f'<div class="in2-grid">{grid}</div>'
        '<h2 class="in2-h">How it flows</h2>'
        '<p class="in2-sub">Three simple stages from secret image to recovered image.</p>'
        f'<div class="in2-flow">{flow}</div>'
        '<div class="in2-gap"></div></div>'
    )


if st.session_state.stage == "cover":
    st.markdown(COVER_CSS.replace("{{BG}}", _bg_uri()), unsafe_allow_html=True)
    st.markdown(COVER_HTML, unsafe_allow_html=True)
    _l, _m, _r = st.columns([2, 1, 2])
    with _m:
        if st.button("Get Started", type="primary", key="start_btn", use_container_width=True):
            st.session_state.stage = "intro"
            st.rerun()
    st.stop()

if st.session_state.stage == "intro":
    st.markdown(INTRO_CSS.replace("{{BG}}", _bg_uri()), unsafe_allow_html=True)
    st.markdown(_intro_html(), unsafe_allow_html=True)
    _a, _b, _c, _d = st.columns([1.3, 1, 1, 1.3])
    with _b:
        if st.button("←  Back", key="back_btn", use_container_width=True):
            st.session_state.stage = "cover"
            st.rerun()
    with _c:
        if st.button("Let's Try  →", type="primary", key="try_btn", use_container_width=True):
            st.session_state.stage = "app"
            st.rerun()
    st.stop()

# ============================== PAGE 2: SIDEBAR NAVIGATION ==============================
NAV = [
    ("Sender", "📤", "Sender"),
    ("Receiver", "📥", "Receiver"),
    ("Demo Steps", "🧭", "Demo Steps"),
]
page = st.session_state.page

with st.sidebar:
    st.markdown(
        '<div class="side-brand"><div class="badge">🔐</div>'
        '<div><div class="name">Quantum Key</div><div class="sub">STEGANOGRAPHY SUITE</div></div></div>'
        '<div class="side-label">WORKSPACE</div>',
        unsafe_allow_html=True,
    )
    for key, icon, label in NAV:
        if st.button(f"{icon}   {label}", key=f"nav_{key}",
                     type="primary" if page == key else "secondary", use_container_width=True):
            st.session_state.page = key
            st.rerun()
    st.markdown('<div class="side-divider"></div>', unsafe_allow_html=True)
    if st.button("🏠   Home", key="nav_home", use_container_width=True):
        st.session_state.stage = "cover"
        st.rerun()
    st.markdown(
        '<div class="side-foot"><div class="t">● End-to-end protected</div>'
        '<div class="d">Quantum key · RSA · AES · GAN</div></div>',
        unsafe_allow_html=True,
    )


_bn = _banner_photo_uri()
if _bn:
    st.markdown(
        '<style>.page-banner { background-image: linear-gradient(90deg, rgba(3,10,20,0.94) 0%, rgba(3,10,20,0.80) 42%, rgba(3,10,20,0.28) 100%), '
        'url("' + _bn + '") !important; }</style>',
        unsafe_allow_html=True,
    )


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


def page_steps(color, items):
    cells = "".join(f'<div class="ps"><div class="n">{i+1}</div><div class="t">{t}</div></div>' for i, t in enumerate(items))
    st.markdown(f'<div class="page-steps {color}">{cells}</div>', unsafe_allow_html=True)


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
if page == "Sender":
    page_banner("blue", "📤", "Sender — Hide a Secret Image",
                "Pick a cover photo and the secret image you want to protect, add the receiver's "
                "public key, and the pipeline handles the quantum key, encryption, and GAN embedding.")

    page_steps("blue", ["Upload cover + secret image", "Add receiver's public key", "Encrypt, hide & download"])

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
    step_heading("blue", "2", "Add the receiver's key & run", "public key + output name")

    kc1, kc2 = st.columns(2)
    with kc1:
        with st.container(border=True):
            info_card_header("blue", "🔑", "Receiver's Public Key",
                              "Wraps the AES key so only the receiver can unlock it — a .pem file")
            pubkey_file = st.file_uploader("Receiver's Public Key (.pem)", type=["pem"], key="pubkey",
                                            label_visibility="collapsed")
    with kc2:
        with st.container(border=True):
            info_card_header("blue", "🏷️", "Output Name", "Base name for the generated message file")
            out_name = st.text_input("Output name", value="message", key="out_send", label_visibility="collapsed")

    st.write("")

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

            with open(bundle_path, "rb") as f:
                bundle_bytes = f.read()
            st.session_state["send_result"] = {
                "cover_resized_path": cover_resized_path,
                "stego_path": stego_path,
                "bundle_path": bundle_path,
                "bundle_bytes": bundle_bytes,
            }

    if "send_result" in st.session_state:
        r = st.session_state["send_result"]
        st.write("")
        step_heading("blue", "3", "Result", "stego image + message file")
        st.success("✅  Secret hidden and encrypted successfully.")

        with st.container(border=True):
            info_card_header("blue", "🧪", "Cover vs Stego",
                              f"Both shown at the model's working resolution ({CFG.IMAGE_SIZE}x{CFG.IMAGE_SIZE}) for a fair comparison")
            c1, c2 = st.columns(2)
            with c1:
                st.image(r["cover_resized_path"], caption="Cover (as the model sees it)", width=320)
            with c2:
                st.image(r["stego_path"], caption="Stego (secret hidden inside)", width=320)

        with st.container(border=True):
            info_card_header("green", "📦", "Message File", "Send this single .qsteg file to the receiver")
            st.download_button(
                "⬇️  Download Message File (.qsteg)",
                data=r["bundle_bytes"], file_name=os.path.basename(r["bundle_path"]),
                mime="application/zip", use_container_width=True, key="dl_bundle",
            )

# ============================== RECEIVER ==============================
if page == "Receiver":
    page_banner("green", "📥", "Receiver — Decrypt & Recover",
                "Generate your keypair once, share the public key with the sender, then drop in the "
                "message file and your private key to recover the original secret image.")

    page_steps("green", ["Generate your keypair", "Upload message file + private key", "Decrypt & download images"])

    step_heading("green", "1", "Your identity", "one-time setup — skip if already generated")

    with st.container(border=True):
        info_card_header("green", "🪪", "Generate Your Keypair",
                          "Creates your RSA public/private key pair for this session")
        if st.button("🔑  Generate My Keys", use_container_width=True):
            os.makedirs(CFG.KEYS_DIR, exist_ok=True)
            priv, pub = generate_receiver_keypair(CFG.RSA_KEY_SIZE)
            priv_path = os.path.join(CFG.KEYS_DIR, "receiver_private_key.pem")
            pub_path = os.path.join(CFG.KEYS_DIR, "receiver_public_key.pem")
            serialize_private_key(priv, priv_path)
            serialize_public_key(pub, pub_path)

            with open(pub_path, "rb") as f:
                st.session_state["pub_key_bytes"] = f.read()
            with open(priv_path, "rb") as f:
                st.session_state["priv_key_bytes"] = f.read()
            st.success("✅  Keys generated.")


        if "pub_key_bytes" in st.session_state:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️  Download Public Key — share with sender",
                                    st.session_state["pub_key_bytes"],
                                    file_name="receiver_public_key.pem",
                                    use_container_width=True, key="dl_pub_key")
            with c2:
                st.download_button("⬇️  Download Private Key — keep confidential",
                                    st.session_state["priv_key_bytes"],
                                    file_name="receiver_private_key.pem",
                                    use_container_width=True, key="dl_priv_key")

    st.write("")
    step_heading("green", "2", "Decrypt and recover a message", "message file + private key")

    col1, col2, col3 = st.columns(3)
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
    with col3:
        with st.container(border=True):
            info_card_header("green", "🏷️", "Output Name", "Base name for the recovered image files")
            out_name_r = st.text_input("Output name", value="message", key="out_recv", label_visibility="collapsed")

    st.write("")

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

            # Store the result in session_state (NEW) instead of only
            # rendering it inline here -- same reasoning as the key-
            # download fix above: reading these bytes now and keeping
            # them around means the images/metrics/download buttons
            # below survive a rerun from clicking either download
            # button, instead of the whole result vanishing after the
            # first download.
            with open(exact_path, "rb") as f:
                exact_bytes = f.read()
            with open(stego_recovered_path, "rb") as f:
                stego_recovered_bytes = f.read()
            st.session_state["receive_result"] = {
                "exact_path": exact_path,
                "stego_recovered_path": stego_recovered_path,
                "exact_bytes": exact_bytes,
                "stego_recovered_bytes": stego_recovered_bytes,
                "log_text": log_text,
            }

    if "receive_result" in st.session_state:
        r = st.session_state["receive_result"]
        st.write("")
        step_heading("green", "3", "Recovered output", "exact + approximate recovery")
        st.success("✅  Secret recovered successfully.")

        with st.container(border=True):
            info_card_header("green", "🖼️", "Recovered Images", "Cryptographic recovery vs. GAN-decoded recovery")
            c1, c2 = st.columns(2)
            with c1:
                st.image(r["exact_path"], caption="Exact Recovery (cryptographic — pixel-perfect)", width=320)
            with c2:
                st.image(r["stego_recovered_path"], caption="Approximate Recovery (via GAN steganography)", width=320)

        match = re.search(r"PSNR:\s*([\d.]+)\s*dB\s*\|\s*SSIM:\s*([\d.]+)", r["log_text"])
        if match:
            mcol1, mcol2 = st.columns(2)
            mcol1.metric("PSNR (Stego Recovery)", f"{match.group(1)} dB")
            mcol2.metric("SSIM (Stego Recovery)", match.group(2))

        with st.container(border=True):
            info_card_header("green", "⬇️", "Downloads", "Save the recovered images")
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button("⬇️  Download Exact Recovery", r["exact_bytes"],
                                    file_name=os.path.basename(r["exact_path"]),
                                    use_container_width=True, key="dl_exact")
            with dl2:
                st.download_button("⬇️  Download Stego Recovery", r["stego_recovered_bytes"],
                                    file_name=os.path.basename(r["stego_recovered_path"]),
                                    use_container_width=True, key="dl_stego_recovered")

# ============================== ABOUT ==============================
if page == "Demo Steps":
    page_banner("violet", "🧭", "Demo Steps — How It Works",
                "A walk-through of the full pipeline, end to end — from the quantum key on the "
                "sender's side to the pixel-exact recovery on the receiver's side.")

    st.markdown(
        '<div class="capability-strip">'
        '<span>Quantum Key Generation</span><span>RSA-2048 Key Exchange</span>'
        '<span>AES-128 CTR Encryption</span><span>GAN-Based Steganography</span>'
        '<span>Adversarial Discriminator Training</span></div>',
        unsafe_allow_html=True,
    )

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
        '<span class="stage-sub">&nbsp;&mdash; the Sender page</span></div>',
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
        '<span class="stage-sub">&nbsp;&mdash; the Receiver page</span></div>',
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