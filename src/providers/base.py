import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from helpers.exceptions import AIProviderError


def _sanitize_for_prompt(text: str, max_length: int = 5000) -> str:
    """Sanitize text for inclusion in AI prompts to mitigate injection."""
    if not text:
        return ""
    return str(text)[:max_length]


class BaseProvider(ABC):
    """Abstract base class for all AI providers.

    This class defines the interface for AI text generation and JSON generation.
    Business logic (resume enhancement, profile analysis) lives in the service layer.
    """

    @abstractmethod
    async def generate_text(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> str:
        """Core method to generate text using the specific provider.

        Args:
            system_prompt: The system or developer instructions for the model.
            user_prompt: The user input or data.
            **kwargs: Provider-specific configuration options.

        Returns:
            str: The generated text response.
        """
        pass

    async def generate_json(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> Dict[str, Any]:
        """Core method to generate JSON using the specific provider.

        Subclasses (e.g., OpenAIProvider) can override this to use native JSON modes.
        Otherwise, this acts as a robust text generation + parsing fallback.
        """
        system_with_json = (
            system_prompt
            + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."
        )
        text = await self.generate_text(system_with_json, user_prompt, **kwargs)

        # Extract JSON from response (handle potential markdown wrapping)
        text = text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            end_marker = text.rfind("```", 3)
            if end_marker > 3:
                inner = text[3:end_marker]
                # Try to chop off the language identifier (e.g., 'json')
                first_newline = inner.find("\n")
                if first_newline >= 0:
                    first_line = inner[:first_newline].strip()
                    if (
                        first_line
                        and not first_line.startswith("{")
                        and not first_line.startswith("[")
                    ):
                        inner = inner[first_newline + 1 :]
                text = inner.strip()

        # Fallback: find JSON object boundaries
        if not text.startswith("{") and not text.startswith("["):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise AIProviderError(f"Failed to parse AI response as JSON: {e}") from e
