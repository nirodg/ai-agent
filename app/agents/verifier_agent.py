"""Verifier: re-research a company and diff against an existing profile.

Also exposes `run_persona_followup` — a re-research-with-different-persona helper
used by the UI to compare two analyses of the same company.
"""

from typing import Optional

from app.config import PERSONA_PRESETS
from app.db import load_all_profiles
from app.services.memory import build_company_memory_block

from .enrichment_agent import enrich_company


def diff_profiles(old: dict, new: dict) -> list[str]:
    """Return a list of human-readable change descriptions between two profiles."""
    changes = []

    def changed(key):
        return str(old.get(key, "")) != str(new.get(key, ""))

    if changed("recent_news"):
        changes.append(f"📰 **News updated:** {new.get('recent_news', '')[:200]}")

    old_fi = old.get("funding_info", {})
    new_fi = new.get("funding_info", {})
    for fk, label in [("total_raised","💰 Funding"), ("last_round","📅 Last round"), ("key_investors","🏦 Investors")]:
        if str(old_fi.get(fk,"")) != str(new_fi.get(fk,"")):
            changes.append(f"{label} changed: {new_fi.get(fk,'Unknown')}")

    old_pains = set(old.get("pain_points", []))
    new_pains = set(new.get("pain_points", []))
    added = new_pains - old_pains
    if added:
        changes.append(f"🎯 New pain points identified: {'; '.join(added)}")

    old_jobs = old.get("job_signals", {})
    new_jobs = new.get("job_signals", {})
    if str(old_jobs.get("hiring_themes","")) != str(new_jobs.get("hiring_themes","")):
        changes.append(f"👥 Hiring themes changed: {new_jobs.get('hiring_themes','Unknown')}")

    old_stack = set(old.get("tech_stack", {}).get("tools_identified", []))
    new_stack = set(new.get("tech_stack", {}).get("tools_identified", []))
    added_tools = new_stack - old_stack
    if added_tools:
        changes.append(f"🛠 New tools detected: {', '.join(added_tools)}")

    return changes if changes else ["No significant changes detected."]


def run_persona_followup(profile: dict, persona_preset: str,
                         depth: Optional[str] = None) -> dict:
    """Re-research the same company with a different persona preset.

    Returns the new full profile dict (with confidence/funding_info/competitors/
    job_signals/tech_stack/search_depth merged in). Caller decides whether to
    persist it.
    """
    followup_prompt = PERSONA_PRESETS[persona_preset]
    full_system_prompt = followup_prompt + build_company_memory_block(load_all_profiles())
    resolved_depth = depth or profile.get("search_depth", "balanced")
    pd_, conf, fi, comps, jobs, stack = enrich_company(
        profile["company_name"],
        full_system_prompt,
        resolved_depth,
    )
    return {
        **pd_,
        "confidence": conf,
        "funding_info": fi,
        "competitors": comps,
        "chat_history": [],
        "search_depth": resolved_depth,
        "job_signals": jobs,
        "tech_stack": stack,
        "id": None,
    }
