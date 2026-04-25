from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from providers.openai import OpenAIProvider
from providers.claude import ClaudeProvider
from providers.image import ImageProvider

if TYPE_CHECKING:
    from config.settings import Settings
    from providers import BaseProvider

logger = logging.getLogger("linkedin-mcp.providers.factory")

def create_ai_provider(settings: Settings) -> BaseProvider | None:
    """Factory to create the configured AI provider."""
    provider_type = settings.ai_provider.lower()
    
    if provider_type == "openai" and settings.openai_api_key:
        logger.debug("Initializing OpenAI provider: %s", settings.ai_model)
        return OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.ai_model,
            api_base=settings.ai_base_url or None,
        )
    
    if provider_type == "claude" and settings.anthropic_api_key:
        logger.debug("Initializing Claude provider: %s", settings.ai_model)
        return ClaudeProvider(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=settings.ai_model,
        )
    
    logger.warning("No valid AI provider configuration found for: %s", provider_type)
    return None

def create_image_provider(settings: Settings) -> ImageProvider | None:
    """Factory to create the configured Image provider."""
    if settings.has_image_gen:
        logger.debug("Initializing Image provider: %s", settings.gemini_image_model)
        return ImageProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_image_model,
        )
    return None
