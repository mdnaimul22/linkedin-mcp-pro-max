"""Anthropic Claude AI provider for content generation."""

from typing import Any, Dict, List, Optional
from providers.base import BaseProvider
from helpers.exceptions import AIProviderError
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "claude_provider.log", name="linkedin-mcp.ai")


class ClaudeProvider(BaseProvider):
    """AI provider using Anthropic Claude for content generation."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise AIProviderError(
                "anthropic package is required. Install with: pip install anthropic"
            )
        self._model = model

    async def generate_text(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> str:
        """Make a Claude API call and return the text response."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=kwargs.get("max_tokens", 4096),
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                temperature=kwargs.get("temperature", 0.7),
            )
            block = response.content[0]
            if not hasattr(block, "text"):
                raise AIProviderError(f"Expected TextBlock, got {type(block)}")
            return str(getattr(block, "text"))
        except Exception as e:
            raise AIProviderError(f"Claude API call failed: {e}") from e
