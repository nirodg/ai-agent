"""Outreach generation: cold email, follow-up sequences, LinkedIn DMs, objection prep."""

import json

from langsmith import traceable

from app.config import TONE_INSTRUCTIONS
from app.llm.factory import invoke_with_provider_fallback


def _base_email_context(profile: dict) -> str:
    pains = "\n".join(f"- {p}" for p in profile.get("pain_points", []))
    jobs  = profile.get("job_signals", {})
    stack = profile.get("tech_stack", {})
    extra = ""
    if jobs.get("pitch_implication") and jobs["pitch_implication"] != "Unknown":
        extra += f"\n- Hiring insight: {jobs['pitch_implication']}"
    if stack.get("pitch_implication") and stack["pitch_implication"] != "Unknown":
        extra += f"\n- Tech stack insight: {stack['pitch_implication']}"
    return f"""
Company: {profile.get('company_name')}
Core product: {profile.get('core_product')}
Recent news: {profile.get('recent_news')}
Pain points:
{pains}
Pitch angle: {profile.get('pitch_angle')}{extra}
""".strip()


@traceable(name="generate_email_draft", tags=["step2", "outreach", "email"])
def generate_email_draft(profile: dict, tone: str) -> str:
    prompt = f"""
You are an expert B2B sales copywriter.
Write a cold outreach email to a decision-maker at {profile['company_name']}.

{_base_email_context(profile)}

TONE: {TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS['formal'])}
RULES:
- Subject line first, prefixed "Subject: "
- Blank line then email body
- Under 200 words
- Single CTA (e.g. 15-min call)
- Sign off as "The Team"
- No "I hope this finds you well"
"""
    return invoke_with_provider_fallback(prompt, temperature=0.7, where="generate_email_draft")


@traceable(name="generate_followup_sequence", tags=["step2", "outreach", "sequence"])
def generate_followup_sequence(profile: dict, tone: str) -> list[dict]:
    """Generate a 3-touch follow-up sequence."""
    prompt = f"""
You are an expert B2B sales copywriter.
Write a 3-email follow-up sequence for {profile['company_name']}.

{_base_email_context(profile)}

TONE: {TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS['formal'])}

Return ONLY a JSON array with exactly 3 objects — no markdown:
[
  {{"touch": 1, "send_gap": "Day 1", "subject": "...", "body": "..."}},
  {{"touch": 2, "send_gap": "Day 4", "subject": "...", "body": "..."}},
  {{"touch": 3, "send_gap": "Day 10", "subject": "...", "body": "..."}}
]
Each email under 150 words. Touch 3 is a short "break-up" email.
Sign off as "The Team". No placeholders.
"""
    try:
        raw = invoke_with_provider_fallback(prompt, temperature=0.7, where="generate_followup_sequence").replace("```json","").replace("```","")
        return json.loads(raw)
    except Exception:
        return []


@traceable(name="generate_linkedin_message", tags=["step2", "outreach", "linkedin"])
def generate_linkedin_message(profile: dict) -> str:
    """Generate a short LinkedIn DM variant."""
    prompt = f"""
Write a LinkedIn cold outreach message for {profile['company_name']}.

{_base_email_context(profile)}

RULES:
- Max 300 characters (LinkedIn connection note limit)
- Conversational, no corporate jargon
- One clear hook + one soft CTA
- No subject line needed
- No sign-off name
"""
    return invoke_with_provider_fallback(prompt, temperature=0.7, where="generate_linkedin_message")


@traceable(name="generate_objection_prep", tags=["step2", "outreach", "objections"])
def generate_objection_prep(profile: dict) -> list[dict]:
    """Generate top 3 objections + rebuttals."""
    prompt = f"""
You are a B2B sales coach.
For {profile['company_name']}, generate the 3 most likely objections
a prospect would raise and a sharp rebuttal for each.

{_base_email_context(profile)}

Return ONLY a JSON array — no markdown:
[
  {{"objection": "...", "rebuttal": "..."}},
  {{"objection": "...", "rebuttal": "..."}},
  {{"objection": "...", "rebuttal": "..."}}
]
"""
    try:
        raw = invoke_with_provider_fallback(prompt, temperature=0.3, where="generate_objection_prep").replace("```json","").replace("```","")
        return json.loads(raw)
    except Exception:
        return []


@traceable(name="generate_enhanced_draft", tags=["step2", "outreach", "enhance"])
def generate_enhanced_draft(profile: dict, base_subject: str,
                            base_body: str, instructions: str, tone: str) -> str:
    prompt = f"""
Improve this cold email draft for {profile['company_name']}.

ORIGINAL:
Subject: {base_subject}
{base_body}

ENHANCEMENT INSTRUCTIONS: {instructions}
TONE: {TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS['formal'])}

Output: Subject line (prefixed "Subject: "), blank line, improved body. Under 200 words. Sign off "The Team".
"""
    return invoke_with_provider_fallback(prompt, temperature=0.7, where="generate_enhanced_draft")


def parse_email(raw: str) -> tuple[str, str]:
    lines, subject, body_lines = raw.splitlines(), "", []
    for line in lines:
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[-1].strip()
        else:
            body_lines.append(line)
    return subject, "\n".join(body_lines).strip()
