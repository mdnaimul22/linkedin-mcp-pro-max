from __future__ import annotations
from typing import TYPE_CHECKING
from providers.openai import OpenAIProvider
from providers.claude import ClaudeProvider
from providers.image import ImageProvider
from config import Settings, setup_logger

if TYPE_CHECKING:
    from config.settings import Settings as SettingsType
    from providers import BaseProvider

logger = setup_logger(Settings.LOG_DIR / "provider.log", name="linkedin-mcp.providers.factory")

def create_ai_provider(settings: SettingsType) -> BaseProvider | None:
    """Factory to create the configured AI provider."""
    provider_type = settings.ai_provider.lower()
    
    if provider_type == "openai" and settings.openai_api_key:
        logger.debug(f"Initializing OpenAI provider: {settings.ai_model}")
        return OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.ai_model,
            api_base=settings.ai_base_url or None,
        )
    
    if provider_type == "claude" and settings.anthropic_api_key:
        logger.debug(f"Initializing Claude provider: {settings.ai_model}")
        return ClaudeProvider(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=settings.ai_model,
        )
    
    logger.warning(f"No valid AI provider configuration found for: {provider_type}")
    return None

def create_image_provider(settings: SettingsType) -> ImageProvider | None:
    """Factory to create the configured Image provider."""
    if settings.has_image_gen:
        logger.debug(f"Initializing Image provider: {settings.gemini_image_model}")
        return ImageProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_image_model,
        )
    return None
