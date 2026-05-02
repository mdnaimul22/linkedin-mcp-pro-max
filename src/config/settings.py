from pathlib import Path
from typing import Optional, Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from .paths import PROJECT_ROOT

class Settings(BaseSettings):
    PROJECT_NAME: str = "LinkedIn-MCP-Pro-Max"
    VERSION: str = "1.0.0"
    ENV: str = Field(default="development", validation_alias="APP_ENV")

    # LinkedIn credentials
    linkedin_email: str = Field(default="", validation_alias="LINKEDIN_EMAIL")
    linkedin_password: SecretStr = Field(default=SecretStr(""), validation_alias="LINKEDIN_PASSWORD")
    linkedin_username: str = Field(default="", validation_alias="LINKEDIN_USERNAME")

    # AI Provider settings
    ai_provider: Literal["claude", "openai", "ensemble"] = Field(default="claude", validation_alias="AI_PROVIDER")
    ai_base_url: str = Field(default="", validation_alias="AI_BASE_URL")
    ai_model: str = Field(default="claude-3-5-sonnet-20241022", validation_alias="AI_MODEL")
    anthropic_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="OPENAI_API_KEY")

    # Browser settings
    headless: bool = Field(default=True, validation_alias="HEADLESS")
    slow_mo: int = Field(default=0, validation_alias="SLOW_MO")
    timeout: int = Field(default=30000, validation_alias="TIMEOUT")
    viewport_width: int = Field(default=1280, validation_alias="VIEWPORT_WIDTH")
    viewport_height: int = Field(default=720, validation_alias="VIEWPORT_HEIGHT")
    user_agent: Optional[str] = Field(default=None, validation_alias="USER_AGENT")
    chrome_path: Optional[str] = Field(default=None, validation_alias="CHROME_PATH")
    cdp_url: Optional[str] = Field(default=None, validation_alias="CDP_URL")
    experimental_persist_derived_session: bool = Field(default=True, validation_alias="LINKEDIN_EXPERIMENTAL_PERSIST_DERIVED_SESSION")

    # Server settings
    transport: Literal["stdio", "streamable-http"] = Field(default="stdio", validation_alias="TRANSPORT")
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    http_path: str = Field(default="/mcp", validation_alias="HTTP_PATH")

    # App Settings & Paths (Use names without leading underscores for Pydantic compatibility)
    raw_log_dir: str = Field(default="logs", validation_alias="LOG_DIR")
    raw_data_dir: str = Field(default=".browser/data", validation_alias="DATA_DIR")
    raw_user_data_dir: str = Field(default=".browser/profile", validation_alias="USER_DATA_DIR")
    raw_templates_dir: str = Field(default="src/templates", validation_alias="TEMPLATES_DIR")
    
    cache_ttl_hours: int = Field(default=24, validation_alias="CACHE_TTL_HOURS")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", validation_alias="LOG_LEVEL")
    trace_mode: Literal["off", "on_error", "always"] = Field(default="on_error", validation_alias="LINKEDIN_TRACE_MODE")
    
    # Image generation settings
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_image_model: str = Field(default="gemini-2.5-flash-image", validation_alias="GEMINI_IMAGE_MODEL")

    # API Limits
    linkedin_rate_limit_cpm: int = Field(default=30, validation_alias="LINKEDIN_RATE_LIMIT_CPM")
    linkedin_max_search_results: int = Field(default=20, validation_alias="LINKEDIN_MAX_SEARCH_RESULTS")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    raw_debug_trace_dir: Optional[str] = Field(default=None, validation_alias="DEBUG_TRACE_DIR")

    # Dynamic CLI Overrides (Non-pydantic fields)
    login: bool = False
    status: bool = False
    logout: bool = False

    def resolve_path(self, val: str) -> Path:
        p = Path(val).expanduser()
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def LOG_DIR(self) -> Path: return self.resolve_path(self.raw_log_dir)
    @property
    def DATA_DIR(self) -> Path: return self.resolve_path(self.raw_data_dir)
    @property
    def USER_DATA_DIR(self) -> Path: return self.resolve_path(self.raw_user_data_dir)
    @property
    def TEMPLATES_DIR(self) -> Path: return self.resolve_path(self.raw_templates_dir)
    @property
    def AUTH_ROOT(self) -> Path: return self.USER_DATA_DIR.parent
    @property
    def debug_trace_dir(self) -> Optional[Path]: return self.resolve_path(self.raw_debug_trace_dir) if self.raw_debug_trace_dir else None
    @property
    def is_production(self) -> bool: return self.ENV.lower() == "production"
    @property
    def has_image_gen(self) -> bool: return bool(self.gemini_api_key)
    
    def validate_config(self) -> list[str]:
        """Validate essential configuration and return advisories."""
        advisories = []
        if not self.linkedin_email and not self.linkedin_username:
            advisories.append("Missing LinkedIn credentials")
        if self.ai_provider == "claude" and not self.anthropic_api_key:
            advisories.append("Missing Anthropic API Key")
        if self.ai_provider == "openai" and not self.openai_api_key:
            advisories.append("Missing OpenAI API Key")
        return advisories

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

# Singleton instance
Settings = Settings()

def get_settings() -> Settings:
    """Compatibility helper to return the global settings singleton."""
    return Settings

def set_settings(new_settings: Settings) -> None:
    """Update the global settings singleton with values from a new instance."""
    global Settings
    Settings = new_settings
