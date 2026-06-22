# /// script
# dependencies = [
#   "langchain-core",
#   "langchain-openai",
#   "langchain-ollama",
#   "langgraph",
#   "pydantic",
#   "ddgs",
#   "streamlit",
#   "python-dotenv",
#   "openpyxl",
#   "tenacity",
#   "langsmith",
# ]
# ///
"""AI Sales Enrichment Agent — Streamlit entrypoint.

Thin shim that wires the `app/` package to Streamlit:
- loads .env
- configures the Streamlit page
- initialises the SQLite database
- initialises session state (incl. LangSmith session id)
- renders the sidebar (returns saved profiles)
- routes to the active page
"""

import os
import uuid

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# PAGE CONFIG  (must run before any other Streamlit call)
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Sales Enrichment Agent",
    page_icon="🚀",
    layout="wide",
)

# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
from app.db import init_db
init_db()

# ---------------------------------------------------------
# SESSION STATE
# LangGraph auto-traces when these env vars are set:
#   LANGSMITH_TRACING=true
#   LANGSMITH_API_KEY=<your key>
#   LANGSMITH_PROJECT=<your project name>
# All three are read from .env via load_dotenv() above.
# `session_id` groups traces per app session.
# ---------------------------------------------------------
os.environ.setdefault("LANGSMITH_PROJECT", "sales-enrichment-agent")

_DEFAULTS = {
    "session_id":               lambda: str(uuid.uuid4()),
    "messages":                 list,
    "viewing_profile_id":       lambda: None,
    "editing_prompt":           lambda: False,
    "bulk_mode":                lambda: False,
    "bulk_results":             list,
    "export_selection":         lambda: "all",
    "last_profile":             lambda: None,
    "search_depth":             lambda: "balanced",
    "current_page":             lambda: "research",
    "conversation_temperature": lambda: 0.7,
}
for _key, _factory in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _factory()

# ---------------------------------------------------------
# UI  (imported after page config + session state)
# ---------------------------------------------------------
from app.ui.alerts_page    import render_trigger_alerts_page
from app.ui.backup_page    import render_backup_page
from app.ui.knowledge_page import render_knowledge_page
from app.ui.langsmith_page import render_langsmith_page
from app.ui.profiles_page  import render_priority_dashboard
from app.ui.research_page  import render_research_page
from app.ui.sidebar        import render_sidebar

# ---------------------------------------------------------
# AUTH GUARD
# Detects missing/placeholder API keys before any page renders.
# Blocks the app and shows a setup form until a valid key is saved.
# ---------------------------------------------------------
from app.db import load_setting, save_setting
from app.llm.settings import get_llm_provider, get_openrouter_api_key


def _provider_key_missing() -> bool:
    provider = get_llm_provider()
    if provider == "openrouter":
        key = get_openrouter_api_key()
        return not key or key.startswith("sk-or-your_")
    if provider == "openai":
        key = (load_setting("openai_api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
        return not key or key.startswith("sk-proj-your_")
    if provider == "perplexity":
        key = (load_setting("pplx_api_key") or os.getenv("PPLX_API_KEY") or "").strip()
        return not key
    return False  # ollama needs no key


if _provider_key_missing():
    _provider = get_llm_provider()
    _labels = {"openrouter": "OpenRouter", "openai": "OpenAI", "perplexity": "Perplexity"}
    _links  = {
        "openrouter": "https://openrouter.ai/keys",
        "openai":     "https://platform.openai.com/api-keys",
        "perplexity": "https://www.perplexity.ai/settings/api",
    }
    _placeholders = {"openrouter": "sk-or-v1-...", "openai": "sk-proj-...", "perplexity": "pplx-..."}
    _setting_keys = {"openrouter": "openrouter_api_key", "openai": "openai_api_key", "perplexity": "pplx_api_key"}

    st.title("🔑 API Key Required")
    st.warning(
        f"No **{_labels.get(_provider, _provider)}** API key is configured. "
        "Enter your key below to get started.",
        icon="⚠️",
    )
    _url = _links.get(_provider)
    if _url:
        st.markdown(f"Don't have a key? [Get one here]({_url})")

    with st.form("_auth_setup"):
        _new_key = st.text_input(
            f"{_labels.get(_provider, _provider)} API key",
            type="password",
            placeholder=_placeholders.get(_provider, "Enter API key"),
        )
        if st.form_submit_button("Save & Continue", type="primary", use_container_width=True):
            _k = _new_key.strip()
            if not _k:
                st.error("Please enter a valid API key.")
            else:
                save_setting(_setting_keys[_provider], _k)
                st.rerun()

    st.divider()
    st.caption(
        "You can also switch providers in **⚙️ LLM Settings** (sidebar) "
        "or set `OPENROUTER_API_KEY` as an environment variable / Streamlit secret."
    )
    st.stop()


all_profiles, all_dicts = render_sidebar()

# ---------------------------------------------------------
# PAGE ROUTER
# ---------------------------------------------------------
page = st.session_state.current_page

if page == "dashboard":
    render_priority_dashboard(all_dicts)
elif page == "knowledge":
    render_knowledge_page()
elif page == "alerts":
    render_trigger_alerts_page(all_dicts)
elif page == "langsmith":
    render_langsmith_page()
elif page == "backup":
    render_backup_page()
else:  # "research"
    render_research_page(all_profiles, all_dicts)
