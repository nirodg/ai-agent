"""Trigger Alerts — re-research a saved company and show what changed."""

import streamlit as st

from app.agents.enrichment_agent import enrich_company
from app.agents.verifier_agent import diff_profiles
from app.db import load_all_profiles, save_profile
from app.llm.settings import get_current_system_prompt
from app.services.memory import build_company_memory_block

from .profile_tabs import render_profile_tabs


def render_trigger_alerts_page(all_dicts: list):
    st.title("🔔 Trigger Alerts — Re-research")
    st.caption("Re-run the full research pipeline on a saved company and see what changed.")

    if not all_dicts:
        st.info("No profiles yet.")
        return

    company_names = [p["company_name"] for p in all_dicts]
    selected_name = st.selectbox("Select company to re-research", company_names)
    old_profile   = next(p for p in all_dicts if p["company_name"] == selected_name)

    col_depth, col_btn, _ = st.columns([2, 2, 6])
    with col_depth:
        depth = st.radio("Depth", ["fast","balanced","deep"],
                         format_func=lambda x: {"fast":"⚡","balanced":"⚖️","deep":"🔬"}[x]+" "+x.title(),
                         horizontal=True, key="alert_depth")
    with col_btn:
        run = st.button("🔄 Re-research Now", type="primary", use_container_width=True)

    if run:
        user_sys = get_current_system_prompt()
        full_sys = user_sys + build_company_memory_block(load_all_profiles())
        with st.spinner(f"Re-researching {selected_name}…"):
            try:
                pd_, conf, fi, comps, jobs, stack = enrich_company(
                    selected_name, full_sys, depth
                )
                new_profile = {**pd_, "confidence": conf, "funding_info": fi,
                               "competitors": comps, "job_signals": jobs,
                               "tech_stack": stack, "search_depth": depth}

                changes = diff_profiles(old_profile, new_profile)

                st.subheader("📊 What Changed")
                for change in changes:
                    if change == "No significant changes detected.":
                        st.info(change)
                    else:
                        st.success(change)

                # Save as a new profile entry
                save_profile(pd_, conf, fi, comps, [], depth, jobs, stack)
                st.info("New profile saved to history.")

                with st.expander("🔍 Full New Profile"):
                    render_profile_tabs(new_profile, key_prefix=f"alert_{selected_name}")

                st.rerun()

            except Exception as e:
                st.error(f"Re-research failed: {e}")
