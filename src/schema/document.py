"""Resume and cover letter models for generation and rendering."""

from pydantic import BaseModel, Field
from typing import Any
from schema.common import SCHEMA_MODEL_CONFIG, Certification, Language, OutputFormat


class ResumeHeader(BaseModel):
    """Resume header information."""

    model_config = SCHEMA_MODEL_CONFIG

    name: str
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""


class ResumeExperience(BaseModel):
    """A work experience entry formatted for resume."""

    model_config = SCHEMA_MODEL_CONFIG

    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    description: str = ""


class ResumeEducation(BaseModel):
    """An education entry formatted for resume."""

    model_config = SCHEMA_MODEL_CONFIG

    school: str
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""


class ResumeContent(BaseModel):
    """Structured resume content for template rendering."""

    model_config = SCHEMA_MODEL_CONFIG

    header: ResumeHeader
    summary: str = ""
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class CoverLetterContent(BaseModel):
    """Structured cover letter content for template rendering."""

    model_config = SCHEMA_MODEL_CONFIG

    date: str
    candidate_name: str
    candidate_contact: str = ""
    recipient: str = ""
    company: str = ""
    job_title: str = ""
    greeting: str = "Dear Hiring Manager,"
    introduction: str = ""
    body_paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    signature: str = ""


class GeneratedDocument(BaseModel):
    """Result of generating a resume or cover letter."""

    model_config = SCHEMA_MODEL_CONFIG

    content: str
    format: OutputFormat
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
