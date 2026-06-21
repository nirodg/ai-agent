"""Static configuration: constants, defaults, presets, query templates, badge styles."""

DB_FILENAME = "enrichment_profiles.db"
BACKUP_DIRNAME = "db_backups"

DEFAULT_MODEL = "openai/gpt-oss-120b:free"
DEFAULT_LLM_PROVIDER = "openrouter"
LLM_PROVIDERS = ("openrouter", "openai", "perplexity", "ollama")
DEFAULT_PROVIDER_MODEL_MAP = {
    "openrouter": "openai/gpt-oss-120b:free",
    "openai": "gpt-5-nano",
    "perplexity": "sonar",
    "ollama": "gpt-oss:120b",
}


def _is_openrouter_free_model(model_name: str) -> bool:
    return (model_name or "").strip().endswith(":free")


DEFAULT_SYSTEM_PROMPT = """\
You are an elite AI Sales Research Agent.

Your responsibilities:
1. ALWAYS use the web search tool.
2. Research the company thoroughly using all provided search queries.
3. Extract:
   - company product / core offering
   - latest news or funding
   - likely pain points
   - sales opportunities
4. Be concise but useful.
5. Never hallucinate fake funding or fake news.
6. Mention uncertainty when data is weak.
"""

PERSONA_PRESETS = {
    "sales_research_strategist": DEFAULT_SYSTEM_PROMPT,
    "pain_point_hunter": """\
You are an elite AI Sales Research Agent focused on uncovering urgent pain points and strong outreach hooks.

Your responsibilities:
1. ALWAYS use the web search tool.
2. Research the company thoroughly using all provided search queries.
3. Extract:
   - company product / core offering
   - latest operational, hiring, or strategic pressure signals
   - likely pain points with emphasis on urgency and business impact
   - crisp sales opportunities tied to those pain points
4. Prioritize specificity, urgency, and concrete hooks for outbound messaging.
5. Never hallucinate fake funding, fake news, or fake operational issues.
6. Mention uncertainty when evidence is weak or indirect.
""",
    "executive_briefing": """\
You are an elite AI Sales Research Agent producing executive-ready briefings for account planning.

Your responsibilities:
1. ALWAYS use the web search tool.
2. Research the company thoroughly using all provided search queries.
3. Extract:
   - company product / core offering
   - latest news or funding with leadership relevance
   - likely strategic risks, growth blockers, and executive priorities
   - sales opportunities framed as concise executive recommendations
4. Write with high signal, sharp prioritization, and leadership-level clarity.
5. Never hallucinate fake funding, fake news, or fake strategic conclusions.
6. Mention uncertainty when data is weak.
""",
}
DEFAULT_PERSONA_PRESET = "sales_research_strategist"
PERSONA_PRESET_LABELS = {
    "sales_research_strategist": "Sales Research Strategist",
    "pain_point_hunter": "Pain Point Hunter",
    "executive_briefing": "Executive Briefing",
}


def get_persona_comparison_note(persona_name: str) -> str:
    persona_name = (persona_name or "").strip().lower()
    notes = {
        "sales_research_strategist": "Balanced baseline analysis with practical sales framing and broad coverage.",
        "pain_point_hunter": "Shifts the angle toward urgent pain points, operational pressure, and sharper outbound hooks.",
        "executive_briefing": "Reframes the same company into a leadership-style summary with strategic priorities and executive implications.",
    }
    return notes.get(persona_name, "Uses a different framing to reinterpret the same analysis from another angle.")


SEARCH_DEPTH_QUERIES = {
    "fast": [
        "{company} company overview",
        "{company} news 2025",
        "{company} funding revenue",
    ],
    "balanced": [
        "{company} company overview product",
        "{company} latest news 2025",
        "{company} funding crunchbase revenue",
        "{company} linkedin employees hiring",
        "{company} competitors market",
    ],
    "deep": [
        "{company} company overview product",
        "{company} latest news press release 2025",
        "{company} funding crunchbase revenue valuation",
        "{company} linkedin employees hiring growth",
        "{company} competitors alternatives",
        "{company} customer reviews pain points problems",
        "{company} technology stack integrations",
        "{company} CEO founder leadership team",
    ],
}

# Step 1 extra query sets (appended on top of depth queries)
JOB_QUERIES = ["{company} jobs hiring 2025", "{company} open roles engineering sales"]
TECHSTACK_QUERIES = ["{company} tech stack tools integrations", "{company} software uses built with"]

TONE_INSTRUCTIONS = {
    "formal":   "Write in a formal, executive business tone. Full sentences, no slang. Suitable for C-suite.",
    "friendly": "Write in a warm, conversational tone. Approachable and human. No jargon.",
    "bold":     "Write in a direct, punchy tone. Short sentences. Strong value claim upfront. No fluff.",
}

BADGE_STYLES = {
    "high":   ("🟢", "#1a7a3c", "#d4edda"),
    "medium": ("🟡", "#856404", "#fff3cd"),
    "low":    ("🔴", "#721c24", "#f8d7da"),
}
