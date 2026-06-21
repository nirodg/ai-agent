"""Aggregate company-profile schemas built on top of evidence models."""

from typing import List

from pydantic import BaseModel, Field

from .evidence import FieldConfidence, FundingInfo, JobSignals, TechStack


class CompetitorProfile(BaseModel):
    company_name: str             = Field(description="Competitor company name.")
    core_product: str             = Field(description="What the competitor sells or does.")
    recent_news:  str             = Field(description="Key recent update for the competitor.")
    pain_points:  List[str]       = Field(description="Business challenges this competitor faces.")
    pitch_angle:  str             = Field(description="How to differentiate against this competitor.")
    confidence:   FieldConfidence = Field(description="Confidence per field.")


class CompanyProfile(BaseModel):
    company_name: str                     = Field(description="The formal name of the company.")
    core_product: str                     = Field(description="Summary of what the company sells or does.")
    recent_news:  str                     = Field(description="Key recent update, funding, or press release.")
    pain_points:  List[str]               = Field(description="Business challenges this company likely faces.")
    pitch_angle:  str                     = Field(description="Tailored value proposition for outreach.")
    confidence:   FieldConfidence         = Field(description="Confidence per field.")
    funding_info: FundingInfo             = Field(description="Funding and financial signals.")
    competitors:  List[CompetitorProfile] = Field(description="2-3 direct competitors with full profiles.")
    job_signals:  JobSignals              = Field(description="Job posting analysis and hiring signals.")
    tech_stack:   TechStack               = Field(description="Inferred technology stack and tools.")
