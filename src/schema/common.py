"""Shared model configuration and common LinkedIn entities."""

from pydantic import BaseModel, ConfigDict
from typing import Literal

# --- Shared Model Configuration ---
SCHEMA_MODEL_CONFIG = ConfigDict(
    from_attributes=True,
    validate_assignment=True,
    extra="ignore",
    frozen=False,
)


class Certification(BaseModel):
    """A certification entry."""

    model_config = SCHEMA_MODEL_CONFIG
    name: str = ""
    authority: str = ""


class Language(BaseModel):
    """A language proficiency entry."""

    model_config = SCHEMA_MODEL_CONFIG
    name: str = ""
    proficiency: str = ""


OutputFormat = Literal["html", "md", "pdf"]
