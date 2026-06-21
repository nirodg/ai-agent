"""Supporting evidence/confidence models referenced by aggregate profile schemas."""

from typing import List

from pydantic import BaseModel, Field


class FieldConfidence(BaseModel):
    core_product: str = Field(description="Confidence level: high, medium, or low")
    recent_news:  str = Field(description="Confidence level: high, medium, or low")
    pain_points:  str = Field(description="Confidence level: high, medium, or low")
    pitch_angle:  str = Field(description="Confidence level: high, medium, or low")
    funding_info: str = Field(description="Confidence level: high, medium, or low")


class FundingInfo(BaseModel):
    total_raised:    str = Field(description="Total funding raised. Use 'Unknown' if not found.")
    last_round:      str = Field(description="Most recent round type and date. Use 'Unknown' if not found.")
    key_investors:   str = Field(description="Notable investors, comma-separated. Use 'Unknown' if not found.")
    revenue_signals: str = Field(description="Revenue, ARR, or headcount signals. Use 'Unknown' if not found.")


class JobSignals(BaseModel):
    open_roles:        List[str] = Field(description="List of notable open roles found (e.g. 'Senior Data Engineer', 'VP Sales'). Empty list if none found.")
    hiring_themes:     str       = Field(description="What the hiring patterns suggest about company priorities. Use 'Unknown' if not found.")
    headcount_signal:  str       = Field(description="Any headcount size or growth signals from job postings. Use 'Unknown' if not found.")
    pitch_implication: str       = Field(description="How these hiring signals should shape the sales pitch.")


class TechStack(BaseModel):
    tools_identified: List[str] = Field(description="List of tools/platforms/frameworks identified (e.g. 'Salesforce', 'AWS', 'React'). Empty list if none found.")
    stack_summary:    str       = Field(description="Brief summary of what the stack reveals about the company's technical maturity. Use 'Unknown' if not found.")
    pitch_implication: str      = Field(description="How the tech stack should shape the sales pitch.")
