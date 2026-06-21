"""Priority Dashboard — companies ranked by intent score."""

import streamlit as st

from app.agents.scoring_agent import compute_intent_score
from app.db import save_intent_score

from .badges import intent_score_badge


def render_priority_dashboard(all_dicts: list):
    st.title("🎯 Priority Dashboard")
    st.caption("Companies ranked by intent score. Scores cached — click Refresh to recompute.")
    if not all_dicts:
        st.info("No profiles yet.")
        return

    col_a, col_b, _ = st.columns([2,2,6])
    with col_a:
        score_all = st.button("🔄 Score / Refresh All", use_container_width=True)
    with col_b:
        filt = st.selectbox("Filter", ["All","🔥 High (8–10)","⚡ Medium (5–7)","❄️ Low (1–4)"],
                            label_visibility="collapsed")
    st.divider()

    if score_all:
        prog = st.progress(0, text="Scoring…")
        for i, p in enumerate(all_dicts):
            prog.progress(i / len(all_dicts), text=f"Scoring {p['company_name']}…")
            sd = compute_intent_score(p)
            save_intent_score(p["id"], sd)
            p["intent_score"] = sd
        prog.progress(1.0, text="✅ Done")
        st.rerun()

    scored = sorted(all_dicts,
                    key=lambda x: (x["intent_score"] or {}).get("score", -1) if x.get("intent_score") else -1,
                    reverse=True)

    def passes(item):
        s = item.get("intent_score")
        if filt == "All": return True
        if not s: return False
        v = s["score"]
        if filt.startswith("🔥"): return v >= 8
        if filt.startswith("⚡"): return 5 <= v <= 7
        return v <= 4

    visible = [x for x in scored if passes(x)]
    if not visible:
        st.info("No companies match the filter.")
        return

    for item in visible:
        intent = item.get("intent_score")
        with st.container(border=True):
            col_n, col_b2, col_btn = st.columns([4,3,2])
            with col_n:
                di = {"fast":"⚡","balanced":"⚖️","deep":"🔬"}.get(item.get("search_depth",""),"")
                st.markdown(f"### {di} {item['company_name']}")
                st.caption(item.get("created_at",""))
            with col_b2:
                if intent:
                    st.markdown(intent_score_badge(intent["score"]), unsafe_allow_html=True)
                else:
                    st.caption("Not scored")
            with col_btn:
                if st.button("Score now", key=f"score_{item['id']}"):
                    with st.spinner("Scoring…"):
                        sd = compute_intent_score(item)
                        save_intent_score(item["id"], sd)
                    st.rerun()

            if intent:
                rp = intent.get("rule_score", 0)
                st.markdown(
                    f'<div style="background:#e9ecef;border-radius:6px;height:6px;margin:4px 0 8px;">'
                    f'<div style="background:#0d6efd;width:{rp}%;height:6px;border-radius:6px;"></div></div>'
                    f'<span style="font-size:.72rem;color:#6c757d;">Rule signal strength: {rp}/100</span>',
                    unsafe_allow_html=True)
                if intent.get("signals"):
                    with st.expander("📡 Triggered signals"):
                        for sig in intent["signals"]: st.markdown(f"- ✅ {sig}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🧠 Reasoning**")
                    st.markdown(intent.get("reasoning","—"))
                with col2:
                    st.markdown("**📋 Recommended Action**")
                    st.markdown(intent.get("recommended_action","—"))
                    st.markdown("**🕐 Best Time to Reach**")
                    st.markdown(intent.get("best_time_to_reach","—"))
                if st.button(f"Open {item['company_name']} →", key=f"jump_{item['id']}"):
                    st.session_state.viewing_profile_id = item["id"]
                    st.session_state.current_page = "research"
                    st.rerun()
