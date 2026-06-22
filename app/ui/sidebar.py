"""Sidebar: navigation, persona, LLM settings, model picker, history, export."""

from datetime import datetime

import streamlit as st

from app.config import (
    DEFAULT_PERSONA_PRESET,
    LLM_PROVIDERS,
    PERSONA_PRESET_LABELS,
    PERSONA_PRESETS,
)
from app.db import (
    add_mcp_server,
    delete_mcp_server,
    delete_profile,
    load_all_profiles,
    load_mcp_servers,
    load_setting,
    row_to_dict,
    save_setting,
    set_mcp_server_enabled,
)
from app.llm.factory import test_ollama_connection
from app.llm.settings import (
    get_current_system_prompt,
    get_llm_model,
    get_llm_provider,
    get_llm_timeout,
    get_ollama_api_key,
    get_ollama_api_key_source,
    get_ollama_base_url,
    get_ollama_insecure_ssl,
    get_openrouter_api_key,
    get_openrouter_base_url,
    get_perplexity_base_url,
    get_persona_preset_for_model,
    reset_system_prompt_for_model,
    save_llm_model_for_provider,
    save_persona_preset_for_model,
    save_system_prompt_for_model,
)
from app.services.export import profiles_to_csv, profiles_to_xlsx


def switch_to_chat():
    st.session_state.viewing_profile_id = None
    st.session_state.conversation_temperature = 0.7


def render_sidebar() -> tuple[list, list]:
    """Render the full sidebar. Returns (all_profiles_rows, all_profiles_dicts)."""

    with st.sidebar:

        # ── NAV ───────────────────────────────────────────
        st.markdown("## 🧭 Navigation")
        pages = [
            ("research",   "🔬 Research"),
            ("dashboard",  "🎯 Dashboard"),
            ("knowledge",  "📚 Knowledge Base"),
            ("alerts",     "🔔 Alerts"),
            ("langsmith",  "🔭 LangSmith"),
            ("backup",     "🗄 Backup"),
        ]
        for page_id, page_label in pages:
            active = st.session_state.current_page == page_id
            if st.button(
                f"{'▶ ' if active else ''}{page_label}",
                use_container_width=True,
                type="primary" if active else "secondary",
                key=f"nav_{page_id}",
            ):
                st.session_state.current_page = page_id
                st.rerun()

        st.divider()

        # ── PERSONA ───────────────────────────────────────
        with st.expander("🧬 Agent Persona", expanded=st.session_state.editing_prompt):
            current_provider = get_llm_provider()
            current_model_name = get_llm_model(current_provider)
            current_preset = get_persona_preset_for_model(current_provider, current_model_name)
            current_prompt = get_current_system_prompt(current_provider, current_model_name)
            preset_options = list(PERSONA_PRESETS.keys())
            selected_preset = st.selectbox(
                "Persona preset",
                options=preset_options,
                index=preset_options.index(current_preset),
                format_func=lambda key: PERSONA_PRESET_LABELS.get(key, key),
                label_visibility="collapsed",
            )
            if selected_preset != current_preset:
                save_persona_preset_for_model(current_provider, current_model_name, selected_preset)
                reset_system_prompt_for_model(current_provider, current_model_name)
                st.session_state.editing_prompt = False; st.rerun()

            st.caption(f"Applies to {current_provider} / {current_model_name}")
            if st.session_state.editing_prompt:
                new_prompt = st.text_area("Prompt", value=current_prompt, height=220, label_visibility="collapsed")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Save", use_container_width=True):
                        save_system_prompt_for_model(current_provider, current_model_name, new_prompt.strip())
                        st.session_state.editing_prompt = False; st.rerun()
                with c2:
                    if st.button("✕ Cancel", use_container_width=True):
                        st.session_state.editing_prompt = False; st.rerun()
            else:
                st.caption(current_prompt[:180] + ("…" if len(current_prompt) > 180 else ""))
                if st.button("✏️ Edit Persona", use_container_width=True):
                    st.session_state.editing_prompt = True; st.rerun()
            if st.button("↺ Reset to Default", use_container_width=True):
                save_persona_preset_for_model(current_provider, current_model_name, DEFAULT_PERSONA_PRESET)
                reset_system_prompt_for_model(current_provider, current_model_name)
                st.session_state.editing_prompt = False; st.rerun()

        # ── LLM SETTINGS ──────────────────────────────────
        with st.expander("⚙️ LLM Settings", expanded=False):
            provider_labels = {
                "openrouter": "OpenRouter",
                "openai": "OpenAI",
                "perplexity": "Perplexity",
                "ollama": "Ollama Cloud (Free Tier)",
            }
            current_provider = get_llm_provider()
            selected_provider = st.selectbox(
                "Provider",
                options=list(LLM_PROVIDERS),
                index=list(LLM_PROVIDERS).index(current_provider),
                format_func=lambda x: provider_labels.get(x, x),
                label_visibility="collapsed",
            )
            if selected_provider != current_provider:
                save_setting("llm_provider", selected_provider)
                st.rerun()

            if current_provider == "openrouter":
                openrouter_base = load_setting("openrouter_base_url") or get_openrouter_base_url()
                openrouter_base_input = st.text_input(
                    "OpenRouter base URL",
                    value=openrouter_base,
                    placeholder="https://openrouter.ai/api/v1",
                    label_visibility="collapsed",
                )
                if openrouter_base_input.strip() != openrouter_base:
                    save_setting("openrouter_base_url", openrouter_base_input.strip())
                    st.rerun()

                openrouter_key = load_setting("openrouter_api_key") or get_openrouter_api_key()
                openrouter_key_input = st.text_input(
                    "OpenRouter API key",
                    value=openrouter_key,
                    type="password",
                    placeholder="sk-or-...",
                    label_visibility="collapsed",
                )
                if openrouter_key_input != openrouter_key:
                    save_setting("openrouter_api_key", openrouter_key_input)
                    st.rerun()

            if current_provider == "perplexity":
                pplx_base = load_setting("pplx_base_url") or get_perplexity_base_url()
                pplx_base_input = st.text_input(
                    "Perplexity base URL",
                    value=pplx_base,
                    placeholder="https://api.perplexity.ai",
                    label_visibility="collapsed",
                )
                if pplx_base_input.strip() != pplx_base:
                    save_setting("pplx_base_url", pplx_base_input.strip())
                    st.rerun()

                pplx_key = load_setting("pplx_api_key")
                pplx_key_input = st.text_input(
                    "Perplexity API key",
                    value=pplx_key,
                    type="password",
                    placeholder="pplx-...",
                    label_visibility="collapsed",
                )
                if pplx_key_input != pplx_key:
                    save_setting("pplx_api_key", pplx_key_input)
                    st.rerun()

            if current_provider == "ollama":
                ollama_base = load_setting("ollama_base_url") or get_ollama_base_url()
                ollama_base_input = st.text_input(
                    "Ollama Cloud base URL",
                    value=ollama_base,
                    placeholder="https://ollama.com",
                    label_visibility="collapsed",
                )
                if ollama_base_input.strip() != ollama_base:
                    save_setting("ollama_base_url", ollama_base_input.strip())
                    st.rerun()

                ollama_insecure_ssl = get_ollama_insecure_ssl()
                ollama_insecure_ssl_input = st.checkbox(
                    "Bypass SSL certificate verification",
                    value=ollama_insecure_ssl,
                    help="Enable this if Ollama Cloud returns an expired or untrusted certificate error.",
                )
                if ollama_insecure_ssl_input != ollama_insecure_ssl:
                    save_setting("ollama_insecure_ssl", "true" if ollama_insecure_ssl_input else "false")
                    st.rerun()

                ollama_key = load_setting("ollama_api_key") or get_ollama_api_key()
                ollama_key_input = st.text_input(
                    "Ollama Cloud API key",
                    value=ollama_key,
                    type="password",
                    placeholder="ollama-...",
                    label_visibility="collapsed",
                )
                if ollama_key_input != ollama_key:
                    save_setting("ollama_api_key", ollama_key_input)
                    st.rerun()

                st.caption(f"API key source: {get_ollama_api_key_source()}")
                if st.button("Test Ollama connection", use_container_width=True):
                    with st.spinner("Testing Ollama Cloud…"):
                        try:
                            result = test_ollama_connection()
                            st.success(f"Ollama Cloud OK: {result[:200]}")
                        except Exception as e:
                            st.error(f"Ollama Cloud test failed: {e}")

            current_timeout = get_llm_timeout()
            timeout_input = st.number_input(
                "Timeout seconds",
                min_value=10,
                max_value=900,
                step=5,
                value=current_timeout,
                label_visibility="collapsed",
            )
            if int(timeout_input) != current_timeout:
                save_setting("llm_timeout", str(int(timeout_input)))
                st.rerun()

        # ── AI MODEL ──────────────────────────────────────
        with st.expander("🤖 AI Model", expanded=False):
            current_provider = selected_provider
            if current_provider == "openrouter":
                available_models = [
                    "openai/gpt-oss-120b:free",
                    "openrouter/owl-alpha:free",
                    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                    "nvidia/nemotron-3-super:free",
                    "poolside/laguna-xs-2:free",
                    "poolside/laguna-m-1:free",
                    "deepseek/deepseek-v4-flash:free",
                    "moonshotai/kimi-k2.6:free",
                    "google/gemma-4-26b-a4b:free",
                    "google/gemma-4-31b:free",
                    "google/lyria-3-pro-preview:free",
                    "google/lyria-3-clip-preview:free",
                    "nvidia/nemotron-3-nano-30b-a3b:free",
                    "nvidia/nemotron-nano-12b-2-vl:free",
                    "qwen/qwen3-next-80b-a3b-instruct:free",
                    "nvidia/nemotron-nano-9b-v2:free",
                    "openai/gpt-oss-20b:free",
                    "z-ai/glm-4.5-air:free",
                    "qwen/qwen3-coder-480b-a35b:free",
                    "venice/uncensored:free",
                    "meta-llama/llama-3.3-70b-instruct:free",
                    "meta-llama/llama-3.2-3b-instruct:free",
                    "nousresearch/hermes-3-405b-instruct:free",
                    "minimax/minimax-m2.5:free",
                    "liquid/lfm2.5-1.2b-thinking:free",
                    "liquid/lfm2.5-1.2b-instruct:free",
                ]
            elif current_provider == "perplexity":
                available_models = [
                    "sonar",
                    "sonar-pro",
                    "sonar-reasoning",
                    "sonar-deep-research",
                ]
            elif current_provider == "ollama":
                available_models = [
                    "gpt-oss:120b",
                ]
            else:
                available_models = [
                    "gpt-5-nano",
                    "gpt-4.1",
                    "gpt-4.1-mini",
                    "gpt-4o",
                    "gpt-4o-mini",
                    "o4-mini",
                ]

            current_model = get_llm_model(current_provider)
            if current_model not in available_models:
                available_models.insert(0, current_model)
            selected_model = st.selectbox(
                "Model",
                options=available_models,
                index=available_models.index(current_model),
                label_visibility="collapsed",
            )
            custom_model = st.text_input(
                "Or enter a custom model name",
                placeholder="e.g. openai/gpt-oss-120b:free or sonar-pro",
                label_visibility="collapsed",
            )
            final_model = custom_model.strip() if custom_model.strip() else selected_model
            can_save_model = True
            if current_provider == "openrouter" and final_model and not final_model.endswith(":free"):
                st.error("OpenRouter models must use a :free suffix.")
                final_model = current_model
                can_save_model = False
            if can_save_model and final_model != current_model:
                save_llm_model_for_provider(current_provider, final_model)
                st.rerun()

        # ── MCP SERVERS ───────────────────────────────────
        with st.expander("🔌 MCP Servers", expanded=False):
            st.caption(
                "Register external MCP servers to give the agent extra tools. "
                "Tools from enabled servers are loaded automatically."
            )
            servers = load_mcp_servers()
            for srv in servers:
                row = row_to_dict(srv) if not isinstance(srv, dict) else srv
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1:
                    target = row.get("command") or row.get("url") or ""
                    st.markdown(f"**{row['name']}**  \n`{row['transport']}` · {target[:40]}")
                with c2:
                    enabled = bool(row.get("enabled", 1))
                    new_enabled = st.toggle(
                        "On", value=enabled, key=f"mcp_en_{row['id']}"
                    )
                    if new_enabled != enabled:
                        set_mcp_server_enabled(row["id"], new_enabled)
                        st.rerun()
                with c3:
                    if st.button("🗑", key=f"mcp_del_{row['id']}"):
                        delete_mcp_server(row["id"])
                        st.rerun()

            with st.form("add_mcp_server", clear_on_submit=True):
                st.caption("Add a server")
                mcp_name = st.text_input("Name", placeholder="my-tools")
                mcp_transport = st.selectbox(
                    "Transport", options=["stdio", "streamable_http", "sse"]
                )
                mcp_command = st.text_input(
                    "Command (stdio)", placeholder="python my_server.py"
                )
                mcp_url = st.text_input(
                    "URL (http/sse)", placeholder="http://localhost:8000/mcp"
                )
                if st.form_submit_button("➕ Add server", use_container_width=True):
                    if mcp_name.strip() and (mcp_command.strip() or mcp_url.strip()):
                        add_mcp_server(
                            mcp_name.strip(), mcp_transport,
                            mcp_command.strip(), mcp_url.strip(),
                        )
                        st.rerun()
                    else:
                        st.error("Provide a name and a command or URL.")

        st.divider()

        # ── PROFILE HISTORY ───────────────────────────────
        st.markdown("## 🗂 Profile History")
        if st.button("➕ New Research", use_container_width=True):
            st.session_state.bulk_mode    = False
            st.session_state.bulk_results = []
            st.session_state.last_profile = None
            st.session_state.current_page = "research"
            switch_to_chat()

        all_profiles = load_all_profiles()
        all_dicts    = [row_to_dict(r) for r in all_profiles]

        if not all_profiles:
            st.caption("No profiles yet.")
        else:
            quick_options = [""] + [str(p["id"]) for p in all_dicts]
            active_profile_id = st.session_state.viewing_profile_id

            def _format_profile_option(opt: str) -> str:
                if not opt:
                    return "Select a profile..."
                p = next((x for x in all_dicts if str(x["id"]) == opt), None)
                if not p:
                    return "Select a profile..."
                di = {"fast": "⚡", "balanced": "⚖️", "deep": "🔬"}.get(p.get("search_depth", ""), "")
                score = (p.get("intent_score") or {}).get("score")
                score_str = f" [{score}/10]" if score else ""
                return f"{di} {p['company_name']}{score_str}"

            default_option = ""
            if active_profile_id is not None and any(str(p["id"]) == str(active_profile_id) for p in all_dicts):
                default_option = str(active_profile_id)

            selected_profile_opt = st.selectbox(
                "Quick profile",
                options=quick_options,
                index=quick_options.index(default_option),
                format_func=_format_profile_option,
                label_visibility="collapsed",
                key="sidebar_profile_quick_select",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Open", use_container_width=True, disabled=not selected_profile_opt):
                    st.session_state.viewing_profile_id = int(selected_profile_opt)
                    st.session_state.bulk_mode = False
                    st.session_state.current_page = "research"
                    st.rerun()
            with c2:
                if st.button("Clear", use_container_width=True):
                    switch_to_chat()
                    st.session_state.current_page = "research"
                    st.rerun()

            with st.expander("Show full profile list", expanded=False):
                for p in all_dicts:
                    col_n, col_d = st.columns([5, 1])
                    with col_n:
                        di    = {"fast":"⚡","balanced":"⚖️","deep":"🔬"}.get(p.get("search_depth",""),"")
                        score = (p.get("intent_score") or {}).get("score")
                        score_str = f" [{score}/10]" if score else ""
                        is_active = st.session_state.viewing_profile_id == p["id"]
                        if st.button(f"{'▶ ' if is_active else ''}{di} {p['company_name']}{score_str}",
                                     key=f"view_{p['id']}", use_container_width=True):
                            st.session_state.viewing_profile_id = p["id"]
                            st.session_state.bulk_mode = False
                            st.session_state.current_page = "research"
                    with col_d:
                        if st.button("🗑", key=f"del_{p['id']}", help=f"Delete {p['company_name']}"):
                            delete_profile(p["id"])
                            if st.session_state.viewing_profile_id == p["id"]: switch_to_chat()
                            st.rerun()
                    st.caption(p["created_at"])

        # ── EXPORT ────────────────────────────────────────
        if all_dicts:
            with st.expander("📤 Export", expanded=False):
                export_choice = st.radio("Profiles", ["All profiles","Choose profiles"], key="export_choice_radio")
                if export_choice == "Choose profiles":
                    sel_ids = [p["id"] for p in all_dicts
                               if st.checkbox(p["company_name"], key=f"export_chk_{p['id']}")]
                    export_profiles = [p for p in all_dicts if p["id"] in sel_ids]
                else:
                    export_profiles = all_dicts
                if export_profiles:
                    ts = datetime.now().strftime("%Y%m%d_%H%M")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("⬇️ CSV", data=profiles_to_csv(export_profiles),
                            file_name=f"leads_{ts}.csv", mime="text/csv", use_container_width=True)
                    with c2:
                        st.download_button("⬇️ Excel", data=profiles_to_xlsx(export_profiles),
                            file_name=f"leads_{ts}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True)
                    st.caption(f"{len(export_profiles)} profile(s)")
                else:
                    st.caption("Select at least one profile.")

        st.divider()
        st.caption("Made with ❤️ by Brage Dorin | MIT Licensed | [GitHub Repo](https://github.com/nirodg/ai-agent)")

    return all_profiles, all_dicts
