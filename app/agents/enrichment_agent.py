"""Core company-enrichment pipeline + dedicated job-signal and tech-stack research."""

import json
import re

from langsmith import traceable
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import JOB_QUERIES, SEARCH_DEPTH_QUERIES, TECHSTACK_QUERIES
from app.llm.factory import build_agent, invoke_with_provider_fallback
from app.schemas import CompanyProfile
from app.tools.web_search import _ddgs_search


# ---------------------------------------------------------------------------
# Known key aliases: maps any casing/concatenation variant → correct snake_case
# Covers: camelCase, PascalCase, concatenated (spaces/underscores stripped),
# and hyphenated forms the LLM might emit.
# ---------------------------------------------------------------------------
_KEY_ALIASES: dict[str, str] = {
    "companyname":      "company_name",
    "coreproduct":      "core_product",
    "recentnews":       "recent_news",
    "painpoints":       "pain_points",
    "pitchangle":       "pitch_angle",
    "fundinginfo":      "funding_info",
    "jobsignals":       "job_signals",
    "techstack":        "tech_stack",
    # FundingInfo
    "totalraised":      "total_raised",
    "lastround":        "last_round",
    "keyinvestors":     "key_investors",
    "revenuesignals":   "revenue_signals",
    # JobSignals
    "openroles":        "open_roles",
    "hiringthemes":     "hiring_themes",
    "headcountsignal":  "headcount_signal",
    "pitchimplication": "pitch_implication",
    # TechStack
    "toolsidentified":  "tools_identified",
    "stacksummary":     "stack_summary",
    # FieldConfidence (same as top-level but repeated for nested dicts)
    "pitchinfo":        "pitch_angle",
}


def _normalize_keys(obj: object) -> object:
    """Recursively rename any aliased/concatenated keys to the canonical snake_case form."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            canonical = _KEY_ALIASES.get(k.lower().replace("_", "").replace("-", "").replace(" ", ""), k)
            out[canonical] = _normalize_keys(v)
        return out
    if isinstance(obj, list):
        return [_normalize_keys(i) for i in obj]
    return obj


def _clean_json_text(raw: str) -> str:
    """Clean an LLM-produced JSON string so it can be parsed reliably.

    Handles:
    - Markdown fences (```json ... ```)
    - Prose before/after the outermost ``{...}`` block
    - Literal control characters (U+0000–U+001F) inside string values
    - Non-breaking spaces (U+00A0) inside string values
    - Markdown bold markers (**text**) inside string *values only*
      NOTE: underscores are intentionally NOT stripped — they appear in field names.
    """
    # 1. Strip markdown fences
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = raw.replace("```", "").strip()

    # 2. Extract the outermost {...} block
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    # 3. Walk character-by-character: fix control chars and NBSP inside strings
    result: list[str] = []
    in_string   = False
    escape_next = False
    for ch in raw:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            result.append(ch)
            in_string = not in_string
            continue
        if in_string:
            if "\x00" <= ch <= "\x1f":
                mapping = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
                result.append(mapping.get(ch, f"\\u{ord(ch):04x}"))
                continue
            if ch == "\u00a0":
                result.append(" ")
                continue
        result.append(ch)

    cleaned = "".join(result)

    # 4. Strip markdown bold (**) from inside string *values* only.
    #    We intentionally do NOT strip * or _ because underscores appear in keys.
    def _strip_bold(m: re.Match) -> str:
        inner = re.sub(r"\*{2}", "", m.group(1))
        return f'"{inner}"'

    cleaned = re.sub(r'"((?:[^"\\]|\\.)*)"', _strip_bold, cleaned)

    return cleaned


def _extract_profile(model, raw_response: str) -> CompanyProfile:
    """Convert a free-form research report into a validated CompanyProfile.

    Strategy:
    1. Ask the model for pure JSON, clean + normalize keys, validate.
    2. If that fails, retry with a shorter/stricter prompt.
    3. Both fail → raise (caught by @retry on enrich_company).
    """
    schema_str = json.dumps(CompanyProfile.model_json_schema(), indent=2)

    def _prompt(report: str) -> str:
        return (
            "You are a JSON serializer. Output ONLY a single JSON object — "
            "no markdown, no prose, no code fences, no comments.\n"
            "Use exactly the field names shown in the schema (snake_case with underscores).\n"
            "All string values must be plain text: no asterisks, no newlines inside values.\n"
            f"Schema:\n{schema_str}\n\n"
            f"SOURCE REPORT:\n{report}"
        )

    def _attempt(report: str) -> CompanyProfile:
        raw_json = model.invoke(_prompt(report)).content.strip()
        cleaned  = _clean_json_text(raw_json)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = json.loads(cleaned)   # let it raise naturally
        data = _normalize_keys(data)
        try:
            return CompanyProfile.model_validate(data)
        except Exception:
            # Last resort: re-serialise the normalised dict and use model_validate_json
            return CompanyProfile.model_validate_json(json.dumps(data))

    try:
        return _attempt(raw_response)
    except Exception as first_err:
        try:
            return _attempt(raw_response[:4000])
        except Exception:
            raise ValueError(
                f"Could not extract a valid CompanyProfile after two attempts. "
                f"Last error: {first_err}"
            ) from first_err


@traceable(name="research_job_signals", tags=["step1", "jobs"])
def research_job_signals(company_name: str) -> dict:
    """Run dedicated job-posting searches and extract structured signals."""
    search_results = []
    for q_tmpl in JOB_QUERIES:
        try:
            results = _ddgs_search(q_tmpl.format(company=company_name), max_results=5)
            search_results.extend(results)
        except Exception:
            pass

    if not search_results:
        return {
            "open_roles": [], "hiring_themes": "Unknown",
            "headcount_signal": "Unknown", "pitch_implication": "Unknown",
        }

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', '')[:200]}"
        for r in search_results[:8]
    )
    prompt = f"""
Analyse these job posting search results for {company_name} and extract structured hiring signals.
Respond ONLY with a JSON object matching this schema — no markdown, no preamble:
{{
  "open_roles": ["role1", "role2"],
  "hiring_themes": "...",
  "headcount_signal": "...",
  "pitch_implication": "..."
}}

SEARCH RESULTS:
{snippets}
"""
    try:
        raw = invoke_with_provider_fallback(prompt, temperature=0, where="research_job_signals").replace("```json","").replace("```","")
        return json.loads(raw)
    except Exception:
        return {
            "open_roles": [], "hiring_themes": "Unknown",
            "headcount_signal": "Unknown", "pitch_implication": "Unknown",
        }


@traceable(name="research_tech_stack", tags=["step1", "tech-stack"])
def research_tech_stack(company_name: str) -> dict:
    """Run dedicated tech-stack searches and extract structured signals."""
    search_results = []
    for q_tmpl in TECHSTACK_QUERIES:
        try:
            results = _ddgs_search(q_tmpl.format(company=company_name), max_results=5)
            search_results.extend(results)
        except Exception:
            pass

    if not search_results:
        return {
            "tools_identified": [], "stack_summary": "Unknown",
            "pitch_implication": "Unknown",
        }

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', '')[:200]}"
        for r in search_results[:8]
    )
    prompt = f"""
Analyse these search results for {company_name} and extract their technology stack and tools.
Respond ONLY with a JSON object — no markdown, no preamble:
{{
  "tools_identified": ["tool1", "tool2"],
  "stack_summary": "...",
  "pitch_implication": "..."
}}

SEARCH RESULTS:
{snippets}
"""
    try:
        raw = invoke_with_provider_fallback(prompt, temperature=0, where="research_tech_stack").replace("```json","").replace("```","")
        return json.loads(raw)
    except Exception:
        return {
            "tools_identified": [], "stack_summary": "Unknown",
            "pitch_implication": "Unknown",
        }


def build_enrichment_prompt(company_name: str, depth: str) -> str:
    queries   = SEARCH_DEPTH_QUERIES[depth]
    formatted = "\n".join(f"{i+1}. {q.format(company=company_name)}" for i, q in enumerate(queries))
    return f"""Research the company: {company_name}

You MUST run ALL of the following search queries before answering.
Do not skip any. Each covers a different data source angle:

{formatted}

After completing all searches, synthesize the results into a comprehensive report covering:
- Core product and business model
- Recent news, press releases, or announcements
- Funding rounds, revenue estimates, headcount signals
- Key pain points and business challenges
- 2-3 direct competitors (research each one too)
- Sales pitch angle

Be specific. Cite uncertainty where data is missing or weak.
"""


@traceable(name="enrich_company", tags=["enrichment", "core"])
@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
)
def enrich_company(company_name: str, full_system_prompt: str, depth: str,
                   include_jobs: bool = True, include_stack: bool = True):
    """Full enrichment pipeline with optional job + stack research."""
    agent, base_model = build_agent(full_system_prompt)
    user_message      = build_enrichment_prompt(company_name, depth)
    result = agent.invoke({"messages": [{"role": "user", "content": user_message}]})
    raw_response      = result["messages"][-1].content

    final_profile: CompanyProfile = _extract_profile(base_model, raw_response)

    d            = final_profile.model_dump()
    confidence   = d.pop("confidence")
    funding_info = d.pop("funding_info")
    competitors  = d.pop("competitors")
    job_signals  = d.pop("job_signals")
    tech_stack   = d.pop("tech_stack")

    for comp in competitors:
        comp["confidence"] = comp.pop("confidence", {})

    # Step 1 — dedicated deep searches (override LLM-inferred values)
    if include_jobs:
        job_signals = research_job_signals(company_name)
    if include_stack:
        tech_stack  = research_tech_stack(company_name)

    return d, confidence, funding_info, competitors, job_signals, tech_stack
