"""LinkedIn job search filter, listing, and detail models."""

from pydantic import BaseModel, Field
from schema.common import SCHEMA_MODEL_CONFIG


class JobSearchFilter(BaseModel):
    """Job search filter parameters."""

    model_config = SCHEMA_MODEL_CONFIG

    keywords: str = ""
    location: str = ""
    distance: int | None = None
    job_type: list[str] | None = None
    experience_level: list[str] | None = None
    remote: bool | None = None
    date_posted: str | None = None
    company: str | None = None


class JobListing(BaseModel):
    """A job listing in search results (summary view)."""

    model_config = SCHEMA_MODEL_CONFIG

    job_id: str
    title: str
    company: str
    location: str
    url: str = ""
    date_posted: str = ""
    applicant_count: int | None = None


class JobDetails(BaseModel):
    """Full job posting details."""

    model_config = SCHEMA_MODEL_CONFIG

    job_id: str
    title: str
    company: str
    location: str
    description: str = ""
    url: str = ""
    employment_type: str = ""
    seniority_level: str = ""
    skills: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    job_functions: list[str] = Field(default_factory=list)
    date_posted: str = ""
    applicant_count: int | None = None
