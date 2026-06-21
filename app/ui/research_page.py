"""Research page: profile-view mode, bulk-enrichment mode, and single-chat mode."""

from datetime import datetime

import streamlit as st

from app.agents.enrichment_agent import (
    build_enrichment_prompt,
    enrich_company,
    research_job_signals,
    research_tech_stack,
    _extract_profile,
)
from app.config import SEARCH_DEPTH_QUERIES
from app.db import save_profile
from app.llm.factory import build_agent
from app.llm.settings import get_current_system_prompt
from app.schemas import CompanyProfile
from app.services.export import profile_to_markdown, profiles_to_csv, profiles_to_xlsx
from app.services.memory import build_company_memory_block

from .profile_tabs import render_profile_tabs
from .sidebar import switch_to_chat


def render_research_page(all_profiles: list, all_dicts: list):
    st.title("🚀 Enterprise Lead Enrichment Chatbot")

    # ── VIEW MODE ─────────────────────────────────────────
    if st.session_state.viewing_profile_id is not None:
        target_id = st.session_state.viewing_profile_id
        matching  = [p for p in all_dicts if p["id"] == target_id]
        if matching:
            p = matching[0]
            st.markdown(f"*Researched on {p['created_at']}*")
            st.divider()
            render_profile_tabs(p, key_prefix=f"view_{p['id']}")
            with st.expander("🛠 Raw JSON"):
                st.json({k: v for k, v in p.items() if k not in ("chat_history","id")})
            if p.get("chat_history"):
                with st.expander("💬 Original Chat"):
                    for msg in p["chat_history"]:
                        with st.chat_message(msg["role"]): st.markdown(msg["content"])
        else:
            st.warning("Profile not found.")
            switch_to_chat()
        return

    # ── CHAT / BULK ───────────────────────────────────────
    col_toggle, col_depth, _ = st.columns([2, 3, 5])
    with col_toggle:
        ml = "🗂 Bulk Mode" if not st.session_state.bulk_mode else "💬 Single Mode"
        if st.button(ml, use_container_width=True):
            st.session_state.bulk_mode    = not st.session_state.bulk_mode
            st.session_state.bulk_results = []
            st.session_state.last_profile = None
            st.rerun()
    with col_depth:
        st.radio("Search depth", ["fast","balanced","deep"],
                 format_func=lambda x: {"fast":"⚡ Fast","balanced":"⚖️ Balanced","deep":"🔬 Deep"}[x],
                 horizontal=True, key="search_depth")
    st.divider()

    # ── BULK ──────────────────────────────────────────────
    if st.session_state.bulk_mode:
        st.subheader("🗂 Bulk Company Enrichment")
        bulk_input = st.text_area("Company names (one per line)", height=160,
                                  placeholder="Stripe\nNotion\nLinear\nVercel")
        if st.button("🚀 Enrich All", type="primary", use_container_width=True) and bulk_input.strip():
            companies     = [c.strip() for c in bulk_input.strip().splitlines() if c.strip()]
            st.session_state.bulk_results = []
            full_sys      = get_current_system_prompt() + build_company_memory_block(all_profiles)
            current_depth = st.session_state.search_depth
            prog = st.progress(0, text="Starting…")
            sta  = st.empty()
            for i, company in enumerate(companies):
                prog.progress(i / len(companies),
                              text=f"Researching **{company}** ({i+1}/{len(companies)})…")
                sta.info(f"🔍 {company}")
                try:
                    pd_, conf, fi, comps, jobs, stack = enrich_company(
                        company, full_sys, current_depth)
                    row = {**pd_, "confidence": conf, "funding_info": fi,
                           "competitors": comps, "job_signals": jobs,
                           "tech_stack": stack, "search_depth": current_depth,
                           "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
                    save_profile(pd_, conf, fi, comps, [], current_depth, jobs, stack)
                    st.session_state.bulk_results.append(row)
                except Exception as e:
                    st.session_state.bulk_results.append({"company_name": company, "error": str(e)})
            prog.progress(1.0, text="✅ All done!")
            sta.empty()
            st.rerun()

        if st.session_state.bulk_results:
            ok   = [r for r in st.session_state.bulk_results if "error" not in r]
            fail = [r for r in st.session_state.bulk_results if "error" in r]
            st.markdown(f"### Results — {len(ok)} enriched, {len(fail)} failed")
            if ok:
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                c1, c2 = st.columns(2)
                with c1: st.download_button("⬇️ CSV",  data=profiles_to_csv(ok),
                    file_name=f"bulk_{ts}.csv", mime="text/csv", use_container_width=True)
                with c2: st.download_button("⬇️ Excel", data=profiles_to_xlsx(ok),
                    file_name=f"bulk_{ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
            for idx, p in enumerate(st.session_state.bulk_results):
                with st.container(border=True):
                    if "error" in p:
                        st.error(f"❌ **{p['company_name']}** — {p['error']}")
                    else:
                        render_profile_tabs(p, key_prefix=f"bulk_{idx}")
            if fail: st.warning(f"{len(fail)} failed.")
        return

    # ── SINGLE CHAT ───────────────────────────────────────
    pc = len(all_profiles)
    if pc:
        names = ", ".join(p["company_name"] for p in all_dicts[:5])
        st.info(f"🧠 **Memory active** — {pc} profiles: {names}"
                + (f" +{pc-5} more" if pc > 5 else ""))
    else:
        st.markdown("""
        This agent researches companies using multi-source search,
        maps competitors, surfaces funding + hiring + tech stack signals,
        scores intent, drafts personalised outreach, and tracks everything locally.
        """)

    st.session_state.conversation_temperature = st.slider(
        "Conversation temperature",
        min_value=0.0,
        max_value=1.5,
        value=float(st.session_state.conversation_temperature),
        step=0.1,
        help="Controls creativity for this conversation. Lower is more deterministic; higher is more exploratory.",
    )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if st.session_state.last_profile:
        lp = st.session_state.last_profile
        with st.container(border=True):
            render_profile_tabs(lp, key_prefix="last")
            with st.expander("🛠 Raw JSON"):
                st.json({k: v for k, v in lp.items() if k != "chat_history"})

    prompt = st.chat_input("Ask about a company…")
    if prompt:
        st.session_state.last_profile = None
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            cd = st.session_state.search_depth
            with st.spinner(f"Researching ({cd} depth, {len(SEARCH_DEPTH_QUERIES[cd])} queries + jobs + stack)…"):
                try:
                    full_sys = (get_current_system_prompt()
                                + build_company_memory_block(all_profiles))
                    agent, base_model = build_agent(
                        full_sys,
                        temperature=float(st.session_state.conversation_temperature),
                    )
                    conversation = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[:-1]
                    ] + [{"role": "user", "content": build_enrichment_prompt(prompt, cd)}]

                    result       = agent.invoke({"messages": conversation})
                    raw_response = result["messages"][-1].content

                    fp: CompanyProfile = _extract_profile(base_model, raw_response)

                    pd_          = fp.model_dump()
                    confidence   = pd_.pop("confidence")
                    funding_info = pd_.pop("funding_info")
                    competitors  = pd_.pop("competitors")
                    job_signals  = pd_.pop("job_signals")
                    tech_stack   = pd_.pop("tech_stack")
                    for comp in competitors:
                        comp["confidence"] = comp.pop("confidence", {})

                    # Dedicated job + stack deep searches
                    company_name = pd_.get("company_name", prompt)
                    job_signals  = research_job_signals(company_name)
                    tech_stack   = research_tech_stack(company_name)

                    pd_full = {
                        **pd_, "confidence": confidence, "funding_info": funding_info,
                        "competitors": competitors, "job_signals": job_signals,
                        "tech_stack": tech_stack, "search_depth": cd,
                    }
                    st.session_state.last_profile = pd_full
                    md = profile_to_markdown(pd_full)
                    st.session_state.messages.append({"role": "assistant", "content": md})
                    save_profile(pd_, confidence, funding_info, competitors,
                                 st.session_state.messages, cd, job_signals, tech_stack)
                    st.rerun()

                except Exception as e:
                    err = f"Error: {e}"
                    st.error(err)
