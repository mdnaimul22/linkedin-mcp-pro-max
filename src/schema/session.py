"""LinkedIn session state models for persistence and runtime tracking."""

from pydantic import BaseModel
from schema.common import SCHEMA_MODEL_CONFIG


class SourceState(BaseModel):
    """Metadata for the primary authenticated LinkedIn profile."""

    model_config = SCHEMA_MODEL_CONFIG

    version: int = 1
    source_runtime_id: str
    login_generation: str
    created_at: str
    profile_path: str
    cookies_path: str


class RuntimeState(BaseModel):
    """Metadata for a derived runtime session."""

    model_config = SCHEMA_MODEL_CONFIG

    version: int = 1
    runtime_id: str
    source_runtime_id: str
    source_login_generation: str
    created_at: str
    committed_at: str
    profile_path: str
    storage_state_path: str
    commit_method: str = "checkpoint_restart"
