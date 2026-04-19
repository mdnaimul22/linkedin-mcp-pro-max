"""Configuration management for LinkedIn MCP server.

Loads settings from .env file and environment variables using Pydantic Settings.
"""

import logging
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("linkedin-mcp.config")

# Default directories
DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent / ".browser"
DEFAULT_USER_DATA_DIR = DEFAULT_ROOT / "profile"
DEFAULT_DATA_DIR = DEFAULT_ROOT / "data"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LinkedIn credentials
    linkedin_username: str = Field(default="", validation_alias="LINKEDIN_USERNAME")
    linkedin_password: SecretStr = Field(
        default=SecretStr(""), validation_alias="LINKEDIN_PASSWORD"
    )

    # AI Provider settings
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="ANTHROPIC_API_KEY"
    )
    openai_api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="OPENAI_API_KEY"
    )
    ai_provider: Literal["claude", "openai", "ensemble"] = Field(
        default="claude", validation_alias="AI_PROVIDER"
    )
    ai_base_url: str = Field(default="", validation_alias="AI_BASE_URL")
    ai_model: str = Field(
        default="claude-3-5-sonnet-20241022", validation_alias="AI_MODEL"
    )

    # Browser settings
    headless: bool = Field(default=True, validation_alias="HEADLESS")
    user_data_dir: Path = Field(
        default=DEFAULT_USER_DATA_DIR, validation_alias="USER_DATA_DIR"
    )
    slow_mo: int = Field(default=0, validation_alias="SLOW_MO")
    timeout: int = Field(default=30000, validation_alias="TIMEOUT")
    viewport_width: int = Field(default=1280, validation_alias="VIEWPORT_WIDTH")
    viewport_height: int = Field(default=720, validation_alias="VIEWPORT_HEIGHT")
    user_agent: str | None = Field(default=None, validation_alias="USER_AGENT")
    chrome_path: str | None = Field(default=None, validation_alias="CHROME_PATH")
    cdp_url: str | None = Field(default=None, validation_alias="CDP_URL")
    experimental_persist_derived_session: bool = Field(
        default=True, validation_alias="LINKEDIN_EXPERIMENTAL_PERSIST_DERIVED_SESSION"
    )

    # Server settings
    transport: Literal["stdio", "streamable-http"] = Field(
        default="stdio", validation_alias="TRANSPORT"
    )
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    path: str = Field(default="/mcp", validation_alias="HTTP_PATH")

    # Application settings
    data_dir: Path = Field(default=DEFAULT_DATA_DIR, validation_alias="DATA_DIR")
    cache_ttl_hours: int = Field(default=24, validation_alias="CACHE_TTL_HOURS")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", validation_alias="LOG_LEVEL"
    )
    trace_mode: Literal["off", "on_error", "always"] = Field(
        default="on_error", validation_alias="LINKEDIN_TRACE_MODE"
    )
    debug_trace_dir: Path | None = Field(
        default=None, validation_alias="LINKEDIN_DEBUG_TRACE_DIR"
    )
    is_interactive: bool = Field(default=False)

    # API Limits
    linkedin_rate_limit_cpm: int = Field(
        default=30, validation_alias="LINKEDIN_RATE_LIMIT_CPM"
    )
    linkedin_max_search_results: int = Field(
        default=20, validation_alias="LINKEDIN_MAX_SEARCH_RESULTS"
    )

    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Image generation settings (Google Gemini — configured via .env)
    gemini_api_key: str = Field(
        default="",
        validation_alias="GEMINI_API_KEY",
    )
    gemini_image_model: str = Field(
        default="gemini-2.5-flash-image",
        validation_alias="GEMINI_IMAGE_MODEL",
    )

    # Session constants
    source_profile_dir_name: str = "profile"
    source_state_file_name: str = "source-state.json"
    runtime_profiles_dir_name: str = "runtimes"
    runtime_state_file_name: str = "runtime-state.json"
    cookies_file_name: str = "cookies.json"

    # Session command flags (CLI-driven,    # Action flags (usually CLI-only, not in .env)
    login: bool = False
    login_auto: bool = False
    status: bool = False
    logout: bool = False

    @field_validator("user_data_dir", "data_dir", mode="before")
    @classmethod
    def expand_paths(cls, v: str | Path) -> Path:
        """Expand ~ in paths."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v.expanduser()

    @model_validator(mode="after")
    def validate_ai_config(self) -> "Settings":
        """Validate AI provider configuration."""
        if self.ai_provider == "claude" and not self.anthropic_api_key:
            logger.warning("Anthropic API Key is missing for Claude provider")
        elif self.ai_provider == "openai" and not self.openai_api_key:
            logger.warning("OpenAI API Key is missing for OpenAI provider")
        elif self.ai_provider == "ensemble":
            if not self.anthropic_api_key or not self.openai_api_key:
                logger.warning(
                    "Both Anthropic and OpenAI keys are required for Ensemble provider"
                )
        return self

    def validate_config(self) -> list[str]:
        """Legacy validation for backward compatibility with cli.py."""
        errors = []
        if not self.linkedin_username:
            errors.append("LINKEDIN_USERNAME is required")
        if not self.linkedin_password.get_secret_value():
            errors.append("LINKEDIN_PASSWORD is required")

        # Pydantic already handles some, but we return list for cli.py compatibility
        if self.ai_provider == "claude" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required for Claude provider")
        if self.ai_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required for OpenAI provider")

        return errors

    @property
    def auth_root(self) -> Path:
        """Return the root directory for all authentication artifacts."""
        return self.user_data_dir.parent

    @property
    def cookies_path(self) -> Path:
        """Return the path for portable bridge cookies."""
        return self.auth_root / self.cookies_file_name

    @property
    def source_state_path(self) -> Path:
        """Return the metadata path for the primary authenticated profile."""
        return self.auth_root / self.source_state_file_name

    @property
    def runtime_profiles_root(self) -> Path:
        """Return the root directory for all derived runtime profiles."""
        return self.auth_root / self.runtime_profiles_dir_name

    @property
    def has_ai(self) -> bool:
        """Whether AI generation is available based on provider."""
        if self.ai_provider == "claude":
            return bool(self.anthropic_api_key.get_secret_value())
        if self.ai_provider == "openai":
            return bool(self.openai_api_key.get_secret_value())
        if self.ai_provider == "ensemble":
            return bool(
                self.anthropic_api_key.get_secret_value()
                and self.openai_api_key.get_secret_value()
            )
        return False

    @property
    def has_image_gen(self) -> bool:
        """Whether image generation is available (Gemini API key configured)."""
        return bool(self.gemini_api_key)

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_profiles_root.mkdir(parents=True, exist_ok=True)


# Singleton pattern for settings
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached settings instance, creating one on first call."""
    global _settings
    if _settings is not None:
        return _settings

    from helpers import is_interactive_environment

    settings = Settings()
    settings.is_interactive = is_interactive_environment()
    settings.ensure_dirs()
    _settings = settings
    return _settings


def set_settings(settings: Settings) -> None:
    """Update the global settings instance."""
    global _settings
    _settings = settings
