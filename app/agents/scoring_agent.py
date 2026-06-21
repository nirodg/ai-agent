"""Intent-scoring engine: rule-based signals + LLM narrative layer."""

import json

from langsmith import traceable

from app.llm.factory import invoke_with_provider_fallback


INTENT_SIGNALS = [
    ("Recent funding round mentioned",
     lambda p: any(w in (p.get("recent_news") or "").lower()
                   for w in ["series","seed","raised","funding","investment","round"]), 25),
    ("Funding total raised is known",
     lambda p: (p.get("funding_info") or {}).get("total_raised","Unknown").lower() != "unknown", 10),
    ("Revenue / headcount signals found",
     lambda p: (p.get("funding_info") or {}).get("revenue_signals","Unknown").lower() != "unknown", 10),
    ("3+ pain points identified",
     lambda p: len(p.get("pain_points") or []) >= 3, 15),
    ("High-confidence core product data",
     lambda p: (p.get("confidence") or {}).get("core_product","low") == "high", 10),
    ("High-confidence recent news",
     lambda p: (p.get("confidence") or {}).get("recent_news","low") == "high", 10),
    ("Researched at deep depth",
     lambda p: p.get("search_depth") == "deep", 10),
    ("Competitors mapped",
     lambda p: len(p.get("competitors") or []) >= 2, 10),
    ("Hiring signals found",
     lambda p: len((p.get("job_signals") or {}).get("open_roles", [])) > 0, 5),
    ("Tech stack identified",
     lambda p: len((p.get("tech_stack") or {}).get("tools_identified", [])) > 0, 5),
]


def compute_rule_score(profile: dict) -> tuple[int, list[str]]:
    score, signals = 0, []
    for desc, test, pts in INTENT_SIGNALS:
        try:
            if test(profile):
                score += pts
                signals.append(desc)
        except Exception:
            pass
    return min(score, 100), signals


@traceable(name="compute_intent_score", tags=["scoring", "intent"])
def compute_intent_score(profile: dict) -> dict:
    rule_score, signals = compute_rule_score(profile)
    prompt = f"""
You are a B2B sales intelligence analyst.
Rule-based score: {rule_score}/100. Triggered signals:
{chr(10).join(f"- {s}" for s in signals) if signals else "- None"}

PROFILE:
- Company: {profile.get('company_name')}
- Product: {profile.get('core_product')}
- News: {profile.get('recent_news')}
- Pains: {"; ".join(profile.get('pain_points') or [])}
- Hiring: {json.dumps(profile.get('job_signals') or {})}
- Stack: {json.dumps(profile.get('tech_stack') or {})}
- Funding: {json.dumps(profile.get('funding_info') or {})}

Respond ONLY with JSON (no markdown):
{{
  "adjusted_score": <1-10>,
  "reasoning": "<2-3 sentences>",
  "recommended_action": "<one concrete next step>",
  "best_time_to_reach": "<timing guidance>"
}}
"""
    try:
        raw    = invoke_with_provider_fallback(prompt, temperature=0, where="compute_intent_score").replace("```json","").replace("```","")
        llm_out = json.loads(raw)
    except Exception:
        llm_out = {
            "adjusted_score": max(1, rule_score // 10),
            "reasoning": "LLM scoring unavailable.",
            "recommended_action": "Review profile manually.",
            "best_time_to_reach": "Unknown",
        }
    return {
        "rule_score":         rule_score,
        "score":              int(llm_out.get("adjusted_score", max(1, rule_score // 10))),
        "signals":            signals,
        "reasoning":          llm_out.get("reasoning", ""),
        "recommended_action": llm_out.get("recommended_action", ""),
        "best_time_to_reach": llm_out.get("best_time_to_reach", ""),
    }
