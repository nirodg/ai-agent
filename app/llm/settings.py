"""Provider/model/persona/system-prompt resolution and persistence."""

import json
import os
from typing import Any, Optional

from app.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_PERSONA_PRESET,
    DEFAULT_PROVIDER_MODEL_MAP,
    DEFAULT_SYSTEM_PROMPT,
    LLM_PROVIDERS,
    PERSONA_PRESETS,
    _is_openrouter_free_model,
)
from app.db import load_setting, save_setting


def _to_int(raw: str, fallback: int) -> int:
    try:
        return int(str(raw).strip())
    except Exception:
        return fallback


def get_llm_provider() -> str:
    raw = (load_setting("llm_provider") or os.getenv("LLM_PROVIDER") or DEFAULT_LLM_PROVIDER).strip().lower()
    return raw if raw in LLM_PROVIDERS else DEFAULT_LLM_PROVIDER


def get_provider_model_map() -> dict:
    raw = load_setting("llm_provider_model_map")
    model_map = {}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                model_map = {str(k): str(v).strip() for k, v in parsed.items() if str(v).strip()}
        except Exception:
            model_map = {}

    changed = False
    for provider, default_model in DEFAULT_PROVIDER_MODEL_MAP.items():
        if not model_map.get(provider):
            model_map[provider] = default_model
            changed = True

    if model_map.get("openrouter") and not _is_openrouter_free_model(model_map["openrouter"]):
        model_map["openrouter"] = DEFAULT_PROVIDER_MODEL_MAP["openrouter"]
        changed = True

    # Silent migration path from legacy single-model setting.
    legacy_model = (load_setting("ai_model") or os.getenv("LLM_MODEL") or "").strip()
    current_provider = get_llm_provider()
    if legacy_model and current_provider != "openrouter" and model_map.get(current_provider) != legacy_model:
        model_map[current_provider] = legacy_model
        changed = True

    if changed:
        save_setting("llm_provider_model_map", json.dumps(model_map))

    return model_map


def save_llm_model_for_provider(provider: str, model_name: str):
    provider = (provider or "").strip().lower()
    model_name = (model_name or "").strip()
    if provider not in LLM_PROVIDERS or not model_name:
        return
    if provider == "openrouter" and not _is_openrouter_free_model(model_name):
        return
    model_map = get_provider_model_map()
    model_map[provider] = model_name
    save_setting("llm_provider_model_map", json.dumps(model_map))
    if provider == get_llm_provider():
        save_setting("ai_model", model_name)


def get_llm_model(provider: Optional[str] = None) -> str:
    provider = (provider or get_llm_provider()).strip().lower()
    model_map = get_provider_model_map()
    scoped = (model_map.get(provider) or "").strip()
    if provider == "openrouter" and scoped and not _is_openrouter_free_model(scoped):
        scoped = ""
    if scoped:
        return scoped
    provider_default = (DEFAULT_PROVIDER_MODEL_MAP.get(provider) or "").strip()
    if provider_default:
        return provider_default
    return (load_setting("ai_model") or os.getenv("LLM_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_openrouter_api_key() -> str:
    return (
        load_setting("openrouter_api_key")
        or os.getenv("OPENROUTER_API_KEY")
        or ""
    ).strip()


def get_openrouter_base_url() -> str:
    return (
        load_setting("openrouter_base_url")
        or os.getenv("OPENROUTER_BASE_URL")
        or "https://openrouter.ai/api/v1"
    ).strip()


def _model_prompt_key(provider: Optional[str] = None, model_name: Optional[str] = None) -> str:
    resolved_provider = (provider or get_llm_provider()).strip().lower()
    resolved_model = (model_name or get_llm_model(resolved_provider)).strip()
    return f"{resolved_provider}:{resolved_model}"


def _load_json_setting_map(key: str) -> dict[str, str]:
    raw = load_setting(key)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(map_key): str(map_value) for map_key, map_value in parsed.items() if str(map_value).strip()}


def get_model_persona_preset_map() -> dict[str, str]:
    preset_map = _load_json_setting_map("llm_model_persona_preset_map")
    changed = False
    for key, preset_name in list(preset_map.items()):
        normalized = preset_name.strip().lower()
        if normalized not in PERSONA_PRESETS:
            preset_map[key] = DEFAULT_PERSONA_PRESET
            changed = True
    if changed:
        save_setting("llm_model_persona_preset_map", json.dumps(preset_map))
    return preset_map


def save_persona_preset_for_model(provider: str, model_name: str, preset_name: str):
    normalized_preset = (preset_name or "").strip().lower()
    if normalized_preset not in PERSONA_PRESETS:
        return
    preset_map = get_model_persona_preset_map()
    preset_map[_model_prompt_key(provider, model_name)] = normalized_preset
    save_setting("llm_model_persona_preset_map", json.dumps(preset_map))


def get_persona_preset_for_model(provider: Optional[str] = None, model_name: Optional[str] = None) -> str:
    key = _model_prompt_key(provider, model_name)
    preset_name = get_model_persona_preset_map().get(key, DEFAULT_PERSONA_PRESET).strip().lower()
    return preset_name if preset_name in PERSONA_PRESETS else DEFAULT_PERSONA_PRESET


def get_model_prompt_map() -> dict[str, str]:
    prompt_map = _load_json_setting_map("llm_model_prompt_map")
    legacy_prompt = (load_setting("system_prompt") or "").strip()
    current_key = _model_prompt_key()
    if legacy_prompt and legacy_prompt != DEFAULT_SYSTEM_PROMPT and not prompt_map.get(current_key):
        prompt_map[current_key] = legacy_prompt
        save_setting("llm_model_prompt_map", json.dumps(prompt_map))
    return prompt_map


def save_system_prompt_for_model(provider: str, model_name: str, prompt: str):
    cleaned_prompt = (prompt or "").strip()
    key = _model_prompt_key(provider, model_name)
    prompt_map = get_model_prompt_map()
    if cleaned_prompt:
        prompt_map[key] = cleaned_prompt
    else:
        prompt_map.pop(key, None)
    save_setting("llm_model_prompt_map", json.dumps(prompt_map))


def reset_system_prompt_for_model(provider: str, model_name: str):
    key = _model_prompt_key(provider, model_name)
    prompt_map = get_model_prompt_map()
    prompt_map.pop(key, None)
    save_setting("llm_model_prompt_map", json.dumps(prompt_map))


def get_current_system_prompt(provider: Optional[str] = None, model_name: Optional[str] = None) -> str:
    key = _model_prompt_key(provider, model_name)
    prompt_map = get_model_prompt_map()
    custom_prompt = (prompt_map.get(key) or "").strip()
    if custom_prompt:
        return custom_prompt
    preset_name = get_persona_preset_for_model(provider, model_name)
    return PERSONA_PRESETS.get(preset_name, DEFAULT_SYSTEM_PROMPT)


def get_llm_timeout() -> int:
    raw = (load_setting("llm_timeout") or os.getenv("LLM_TIMEOUT") or "30").strip()
    return _to_int(raw, 30)


def get_perplexity_api_key() -> str:
    return (
        load_setting("pplx_api_key")
        or os.getenv("PPLX_API_KEY")
        or os.getenv("PERPLEXITY_API_KEY")
        or ""
    ).strip()


def get_perplexity_base_url() -> str:
    return (load_setting("pplx_base_url") or os.getenv("PPLX_BASE_URL") or "https://api.perplexity.ai").strip()


def get_ollama_api_key() -> str:
    return (
        os.getenv("OLLAMA_CLOUD_API_KEY")
        or os.getenv("OLLAMA_API_KEY")
        or load_setting("ollama_api_key")
        or ""
    ).strip()


def get_ollama_api_key_source() -> str:
    if os.getenv("OLLAMA_CLOUD_API_KEY"):
        return "environment: OLLAMA_CLOUD_API_KEY"
    if os.getenv("OLLAMA_API_KEY"):
        return "environment: OLLAMA_API_KEY"
    if load_setting("ollama_api_key"):
        return "saved setting: ollama_api_key"
    return "missing"


def get_ollama_base_url() -> str:
    return (
        load_setting("ollama_base_url")
        or os.getenv("OLLAMA_BASE_URL")
        or os.getenv("OLLAMA_CLOUD_BASE_URL")
        or "https://ollama.com"
    ).strip()


def get_ollama_insecure_ssl() -> bool:
    raw_value = (
        load_setting("ollama_insecure_ssl")
        or os.getenv("OLLAMA_INSECURE_SSL")
        or "true"
    ).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def get_ollama_client_kwargs(timeout_seconds: int) -> dict[str, Any]:
    client_kwargs: dict[str, Any] = {"timeout": timeout_seconds}
    api_key = get_ollama_api_key()
    if api_key:
        client_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
    if get_ollama_insecure_ssl():
        client_kwargs["verify"] = False
    return client_kwargs
