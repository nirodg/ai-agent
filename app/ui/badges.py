"""Streamlit-only badge and diff rendering helpers."""

import difflib

import streamlit as st

from app.config import BADGE_STYLES


def confidence_badge(level: str) -> str:
    level = (level or "low").lower()
    icon, color, bg = BADGE_STYLES.get(level, BADGE_STYLES["low"])
    return (f'<span style="background:{bg};color:{color};padding:2px 8px;'
            f'border-radius:12px;font-size:.75rem;font-weight:600;">{icon} {level.upper()}</span>')


def intent_score_badge(score: int) -> str:
    if score >= 8:   color, bg, label = "#1a7a3c", "#d4edda", "🔥 HIGH"
    elif score >= 5: color, bg, label = "#856404", "#fff3cd", "⚡ MEDIUM"
    else:            color, bg, label = "#721c24", "#f8d7da", "❄️ LOW"
    return (f'<span style="background:{bg};color:{color};padding:3px 10px;'
            f'border-radius:12px;font-size:.85rem;font-weight:700;">{label} &nbsp; {score}/10</span>')


def render_diff(original: str, enhanced: str):
    differ    = difflib.HtmlDiff(wrapcolumn=60)
    diff_html = differ.make_table(
        original.splitlines(), enhanced.splitlines(),
        fromdesc="Original", todesc="Enhanced", context=True, numlines=2,
    )
    st.markdown(f"""
    <style>
      .diff{{font-family:monospace;font-size:.82rem;width:100%;border-collapse:collapse}}
      .diff td{{padding:2px 6px;vertical-align:top;white-space:pre-wrap;word-break:break-word}}
      .diff_header{{background:#f0f0f0;font-weight:bold}}
      td.diff_next{{display:none}}
      .diff_add{{background:#d4edda}}.diff_chg{{background:#fff3cd}}.diff_sub{{background:#f8d7da}}
    </style>{diff_html}""", unsafe_allow_html=True)
