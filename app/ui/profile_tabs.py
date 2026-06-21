"""Profile rendering: 5-tab profile view, notes, persona-followup prompt."""

import streamlit as st

from app.agents.verifier_agent import run_persona_followup
from app.config import (
    PERSONA_PRESET_LABELS,
    PERSONA_PRESETS,
    get_persona_comparison_note,
)
from app.db import delete_note, load_notes, save_note
from app.llm.settings import (
    get_llm_model,
    get_llm_provider,
    get_persona_preset_for_model,
)

from .badges import confidence_badge
from .outreach_page import render_email_expander


def render_notes_expander(company_name: str, key_prefix: str):
    with st.expander("📝 Notes & Activity Log"):
        note_input = st.text_area("Add a note", placeholder="e.g. Called VP Sales, follow up in 2 weeks…",
                                  height=80, key=f"note_input_{key_prefix}")
        if st.button("Add Note", key=f"add_note_{key_prefix}") and note_input.strip():
            save_note(company_name, note_input.strip())
            st.success("Note saved")
            st.rerun()
        notes = load_notes(company_name)
        if notes:
            st.divider()
            for n in notes:
                col_txt, col_del = st.columns([6, 1])
                with col_txt:
                    st.markdown(f"**{n['created_at']}** — {n['note']}")
                with col_del:
                    if st.button("🗑", key=f"del_note_{n['id']}"):
                        delete_note(n["id"]); st.rerun()
        else:
            st.caption("No notes yet.")


def render_overview_tab(p: dict, key_prefix: str):
    conf = p.get("confidence", {})
    for field, label in [
        ("core_product", "Core Product"),
        ("recent_news",  "Recent News"),
    ]:
        st.markdown(f"**{label}** &nbsp; {confidence_badge(conf.get(field,'low'))}",
                    unsafe_allow_html=True)
        st.markdown(p.get(field, ""))

    st.markdown(f"**🎯 Pain Points** &nbsp; {confidence_badge(conf.get('pain_points','low'))}",
                unsafe_allow_html=True)
    for pt in p.get("pain_points", []):
        st.markdown(f"- {pt}")

    st.markdown(f"**💡 Sales Pitch Angle** &nbsp; {confidence_badge(conf.get('pitch_angle','low'))}",
                unsafe_allow_html=True)
    st.markdown(p.get("pitch_angle", ""))

    render_email_expander(p, key_prefix)
    render_notes_expander(p.get("company_name",""), key_prefix)


def render_funding_tab(funding: dict, conf: dict):
    st.markdown(f"**💰 Total Raised** &nbsp; {confidence_badge(conf.get('funding_info','low'))}",
                unsafe_allow_html=True)
    st.markdown(funding.get("total_raised", "Unknown"))
    st.markdown("**📅 Last Round**"); st.markdown(funding.get("last_round", "Unknown"))
    st.markdown("**🏦 Key Investors**"); st.markdown(funding.get("key_investors", "Unknown"))
    st.markdown("**📊 Revenue / Headcount Signals**"); st.markdown(funding.get("revenue_signals", "Unknown"))


def render_jobs_tab(job_signals: dict):
    if not job_signals or job_signals.get("hiring_themes") == "Unknown":
        st.info("No job signal data. Re-research with Deep depth to populate this tab.")
        return
    open_roles = job_signals.get("open_roles", [])
    if open_roles:
        st.markdown("**👥 Open Roles Detected**")
        for role in open_roles:
            st.markdown(f"- {role}")
    st.markdown("**📈 Hiring Themes**")
    st.markdown(job_signals.get("hiring_themes", "Unknown"))
    st.markdown("**🔢 Headcount Signal**")
    st.markdown(job_signals.get("headcount_signal", "Unknown"))
    st.markdown("**💡 Pitch Implication**")
    st.markdown(job_signals.get("pitch_implication", "Unknown"))


def render_stack_tab(tech_stack: dict):
    if not tech_stack or tech_stack.get("stack_summary") == "Unknown":
        st.info("No tech stack data. Re-research with Deep depth to populate this tab.")
        return
    tools = tech_stack.get("tools_identified", [])
    if tools:
        st.markdown("**🛠 Tools & Platforms Identified**")
        cols = st.columns(min(len(tools), 4))
        for i, tool_name in enumerate(tools):
            cols[i % 4].markdown(
                f'<span style="background:#e9ecef;padding:3px 8px;border-radius:8px;'
                f'font-size:.8rem;">{tool_name}</span>', unsafe_allow_html=True)
    st.markdown("**📋 Stack Summary**")
    st.markdown(tech_stack.get("stack_summary", "Unknown"))
    st.markdown("**💡 Pitch Implication**")
    st.markdown(tech_stack.get("pitch_implication", "Unknown"))


def render_competitors_tab(competitors: list, key_prefix: str):
    if not competitors:
        st.info("No competitor data found.")
        return
    for i, comp in enumerate(competitors):
        with st.container(border=True):
            st.markdown(f"### 🏢 {comp.get('company_name','Unknown')}")
            conf = comp.get("confidence", {})
            for field, label in [("core_product","Core Product"),("recent_news","Recent News")]:
                st.markdown(f"**{label}** &nbsp; {confidence_badge(conf.get(field,'low'))}",
                            unsafe_allow_html=True)
                st.markdown(comp.get(field, ""))
            st.markdown(f"**🎯 Pain Points** &nbsp; {confidence_badge(conf.get('pain_points','low'))}",
                        unsafe_allow_html=True)
            for pt in comp.get("pain_points", []):
                st.markdown(f"- {pt}")
            st.markdown(f"**💡 Differentiation** &nbsp; {confidence_badge(conf.get('pitch_angle','low'))}",
                        unsafe_allow_html=True)
            st.markdown(comp.get("pitch_angle", ""))
            render_email_expander(comp, key_prefix=f"{key_prefix}_comp{i}")


def render_persona_followup_prompt(p: dict, key_prefix: str = ""):
    current_provider = get_llm_provider()
    current_model_name = get_llm_model(current_provider)
    current_preset = get_persona_preset_for_model(current_provider, current_model_name)
    followup_options = [preset for preset in PERSONA_PRESETS.keys() if preset != current_preset]
    if not followup_options:
        return

    followup_state_key = f"persona_followup_result_{key_prefix}"
    followup_meta_key = f"persona_followup_meta_{key_prefix}"
    with st.container(border=True):
        st.markdown("#### 🔁 Analyze further with a different persona")
        st.caption("Pick a different persona for a second pass on this analysis.")
        selected_followup = st.selectbox(
            "Follow-up persona",
            options=followup_options,
            format_func=lambda key: PERSONA_PRESET_LABELS.get(key, key),
            key=f"persona_followup_select_{key_prefix}",
            label_visibility="collapsed",
        )
        if st.button("Run follow-up analysis", key=f"persona_followup_run_{key_prefix}", use_container_width=True):
            with st.spinner("Running follow-up analysis…"):
                try:
                    followup_profile = run_persona_followup(
                        p,
                        selected_followup,
                        depth=p.get("search_depth", st.session_state.search_depth),
                    )
                    st.session_state[followup_meta_key] = {
                        "persona": selected_followup,
                        "note": get_persona_comparison_note(selected_followup),
                    }
                    st.session_state[followup_state_key] = followup_profile
                    st.success(f"Follow-up analysis complete with {PERSONA_PRESET_LABELS.get(selected_followup, selected_followup)}.")
                except Exception as e:
                    st.error(f"Follow-up analysis failed: {e}")

    followup_profile = st.session_state.get(followup_state_key)
    if followup_profile:
        followup_meta = st.session_state.get(followup_meta_key, {})
        with st.expander("🧭 Follow-up Analysis", expanded=False):
            if followup_meta.get("persona"):
                st.caption(
                    f"Persona: {PERSONA_PRESET_LABELS.get(followup_meta['persona'], followup_meta['persona'])} — {followup_meta.get('note', '')}"
                )
            render_profile_tabs(followup_profile, key_prefix=f"{key_prefix}_followup", include_followup=False)


def render_profile_tabs(p: dict, key_prefix: str = "", include_followup: bool = True):
    depth_badge = {"fast":"⚡ Fast","balanced":"⚖️ Balanced","deep":"🔬 Deep"}.get(p.get("search_depth",""),"")
    st.markdown(f"### 🏢 {p['company_name']}  &nbsp; <small>{depth_badge}</small>",
                unsafe_allow_html=True)

    tab_ov, tab_fi, tab_jobs, tab_stack, tab_comp = st.tabs(
        ["📋 Overview", "💰 Funding", "👥 Job Signals", "🛠 Tech Stack", "🏆 Competitors"]
    )
    kp = key_prefix or p.get("company_name","p").replace(" ","_")
    with tab_ov:    render_overview_tab(p, kp)
    with tab_fi:    render_funding_tab(p.get("funding_info",{}), p.get("confidence",{}))
    with tab_jobs:  render_jobs_tab(p.get("job_signals",{}))
    with tab_stack: render_stack_tab(p.get("tech_stack",{}))
    with tab_comp:  render_competitors_tab(p.get("competitors",[]), kp)
    if include_followup:
        render_persona_followup_prompt(p, kp)
