"""LangSmith stats fetcher (cached) + session metadata helper.

Note: this module imports streamlit because `fetch_langsmith_stats` is decorated
with `@st.cache_data`. This is a deliberate exception to the no-streamlit rule
in non-UI modules — keeping the cache and the LangSmith API call together is
simpler than scattering them.
"""

import os

import streamlit as st
from langsmith import Client as LangSmithClient


LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "sales-enrichment-agent")


def _ls_metadata(company: str = "", operation: str = "") -> dict:
    """Standard metadata attached to every traceable call."""
    return {
        "session_id":  st.session_state.get("session_id", ""),
        "company":     company,
        "operation":   operation,
        "app_version": "3.0",
    }


@st.cache_data(ttl=60)
def fetch_langsmith_stats(project: str) -> dict:
    """Pull run stats from LangSmith API. Cached for 60s."""
    try:
        client = LangSmithClient()
        runs   = list(client.list_runs(
            project_name=project,
            execution_order=1,   # top-level runs only
            limit=200,
        ))
        if not runs:
            return {"error": None, "runs": 0, "total_tokens": 0,
                    "total_cost": 0.0, "errors": 0, "ops": {}}

        total_tokens = sum(getattr(r, "total_tokens", 0) or 0 for r in runs)
        total_cost   = sum(float(getattr(r, "total_cost", 0) or 0) for r in runs)
        error_count  = sum(1 for r in runs if getattr(r, "error", None))

        # Breakdown by operation name (traceable function name)
        ops: dict[str, dict] = {}
        for r in runs:
            name = r.name or "unknown"
            if name not in ops:
                ops[name] = {"count": 0, "errors": 0, "tokens": 0}
            ops[name]["count"]  += 1
            ops[name]["errors"] += 1 if getattr(r, "error", None) else 0
            ops[name]["tokens"] += getattr(r, "total_tokens", 0) or 0

        return {
            "error":        None,
            "runs":         len(runs),
            "total_tokens": total_tokens,
            "total_cost":   total_cost,
            "errors":       error_count,
            "ops":          ops,
        }
    except Exception as e:
        return {"error": str(e), "runs": 0, "total_tokens": 0,
                "total_cost": 0.0, "errors": 0, "ops": {}}
