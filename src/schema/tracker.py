"""Job application tracking models and status enums."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from schema.common import SCHEMA_MODEL_CONFIG

StatusType = Literal[
    "interested", "applied", "interviewing", "offered", "rejected", "withdrawn"
]
VALID_STATUSES = [
    "interested",
    "applied",
    "interviewing",
    "offered",
    "rejected",
    "withdrawn",
]


class TrackedApplication(BaseModel):
    """A tracked job application (stored locally)."""

    model_config = SCHEMA_MODEL_CONFIG

    job_id: str
    job_title: str
    company: str
    status: StatusType = "interested"
    applied_date: str | None = None
    notes: str = ""
    url: str = ""
    resume_used: str | None = None
    cover_letter_used: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TrackingConfig(BaseModel):
    """Configuration for application tracking."""

    model_config = SCHEMA_MODEL_CONFIG

    tracking_enabled: bool = True
    tracking_file: str = "applications.json"
