"""LangSmith Observability page."""

import os

import streamlit as st

from app.services.langsmith_client import LANGSMITH_PROJECT, fetch_langsmith_stats


def render_langsmith_page():
    st.title("🔭 LangSmith Observability")

    tracing_on = os.environ.get("LANGSMITH_TRACING", "").lower() == "true"
    api_key    = os.environ.get("LANGSMITH_API_KEY", "")
    project    = os.environ.get("LANGSMITH_PROJECT", LANGSMITH_PROJECT)

    # Status banner
    if tracing_on and api_key:
        st.success(f"✅ Tracing **active** — project: `{project}`")
    else:
        st.warning(
            "⚠️ Tracing is **off**. Add these to your `.env` file to enable:\n\n"
            "```\nLANGSMITH_TRACING=true\n"
            "LANGSMITH_API_KEY=<your key>\n"
            "LANGSMITH_PROJECT=sales-enrichment-agent\n```"
        )
        return

    # Project link
    st.markdown(
        f"[🌐 Open LangSmith Dashboard](https://smith.langchain.com/projects/{project})",
        unsafe_allow_html=False,
    )

    col_refresh, _ = st.columns([2, 8])
    with col_refresh:
        if st.button("🔄 Refresh Stats"):
            fetch_langsmith_stats.clear()
            st.rerun()

    st.divider()

    stats = fetch_langsmith_stats(project)

    if stats.get("error"):
        st.error(f"Could not fetch stats: {stats['error']}")
        st.caption("Check that your LANGSMITH_API_KEY is correct and has read access.")
        return

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs",    stats["runs"])
    col2.metric("Total Tokens",  f"{stats['total_tokens']:,}")
    col3.metric("Est. Cost",     f"${stats['total_cost']:.4f}")
    col4.metric("Errors",        stats["errors"],
                delta=f"{(stats['errors']/max(stats['runs'],1)*100):.1f}% error rate",
                delta_color="inverse")

    st.divider()
    st.markdown("### 📊 Runs by Operation")

    ops = stats.get("ops", {})
    if ops:
        sorted_ops = sorted(ops.items(), key=lambda x: x[1]["count"], reverse=True)
        for op_name, op_stats in sorted_ops:
            err_rate = op_stats["errors"] / max(op_stats["count"], 1) * 100
            col_n, col_c, col_e, col_t = st.columns([4, 2, 2, 2])
            col_n.markdown(f"**{op_name}**")
            col_c.metric("Runs",   op_stats["count"], label_visibility="collapsed")
            col_e.metric("Errors", op_stats["errors"],
                         delta=f"{err_rate:.0f}%",
                         delta_color="inverse" if op_stats["errors"] else "off",
                         label_visibility="collapsed")
            col_t.metric("Tokens", f"{op_stats['tokens']:,}", label_visibility="collapsed")
    else:
        st.info("No run data yet. Start researching companies to generate traces.")

    st.divider()
    st.markdown("### 🧵 Current Session")
    st.caption(f"Session ID: `{st.session_state.get('session_id','—')}`")
    st.markdown(
        "All traces in this session are tagged with the above ID. "
        "Filter by `session_id` in LangSmith to see only this session's runs."
    )

    with st.expander("⚙️ Required .env variables"):
        st.code(
            "LANGSMITH_TRACING=true\n"
            f"LANGSMITH_API_KEY=<your key>\n"
            f"LANGSMITH_PROJECT={project}\n"
            "OPENAI_API_KEY=<your key>",
            language="bash",
        )
