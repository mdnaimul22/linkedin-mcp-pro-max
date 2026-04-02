"""LinkedIn profile, experience, education, and company models."""

from pydantic import BaseModel, Field
from schema.common import SCHEMA_MODEL_CONFIG, Certification, Language


class Experience(BaseModel):
    """A work experience entry."""

    model_config = SCHEMA_MODEL_CONFIG

    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    description: str = ""


class Education(BaseModel):
    """An education entry."""

    model_config = SCHEMA_MODEL_CONFIG

    school: str
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""


class Profile(BaseModel):
    """LinkedIn user profile."""

    model_config = SCHEMA_MODEL_CONFIG

    profile_id: str
    name: str
    headline: str = ""
    summary: str = ""
    location: str = ""
    industry: str = ""
    email: str = ""
    phone: str = ""
    profile_url: str = ""
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class CompanyInfo(BaseModel):
    """LinkedIn company information."""

    model_config = SCHEMA_MODEL_CONFIG

    company_id: str
    name: str
    tagline: str = ""
    description: str = ""
    website: str = ""
    industry: str = ""
    company_size: str = ""
    headquarters: str = ""
    specialties: list[str] = Field(default_factory=list)
    url: str = ""
