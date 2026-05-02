from __future__ import annotations

import mimetypes
import tempfile
import asyncio
from typing import Any

from helpers.exceptions import AIProviderError
from config import Settings, setup_logger, ensure_dir

logger = setup_logger(Settings.LOG_DIR / "provider.log", name="linkedin-mcp.providers.image")


class ImageProvider:
    """
    Image generation client backed by Google Gemini.

    Usage:
        provider = ImageProvider(api_key="AIza...", model="gemini-2.5-flash-preview-image-generation")
        path = await provider.generate_and_download("a futuristic city")
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.5-flash-image",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None  # lazy init

    def _get_client(self):
        """Lazily initialize the Gemini client."""
        if self._client is not None:
            return self._client

        if not self._api_key:
            raise AIProviderError(
                "GEMINI_API_KEY not configured. Set it in .env to enable image generation."
            )

        from google import genai
        self._client = genai.Client(api_key=self._api_key)
        return self._client

    # ── Core ─────────────────────────────────────────────────────────────────

    async def generate_and_download(
        self,
        prompt: str,
        suffix: str = ".png",
        directory: Any | None = None,
    ) -> Any:
        """
        Generate an image via Gemini and save it to a local file.

        Gemini returns image data inline (not as a URL), so this method
        is the primary interface. There is no separate generate_image()
        returning a URL.

        Args:
            prompt:    Detailed image generation prompt.
            suffix:    Fallback file extension (auto-detected from mime type).
            directory: Directory to save the file in (default: system temp).

        Returns:
            Path to the saved image file.

        Raises:
            AIProviderError: If generation fails.
        """
        if not prompt or not prompt.strip():
            raise AIProviderError("Image prompt cannot be empty.")

        client = self._get_client()

        from google.genai import types

        logger.info(
            f"Generating image via Gemini (model={self._model}, prompt_len={len(prompt)})"
        )

        config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt.strip())],
            ),
        ]

        # Use synchronous streaming in an async context via run_in_executor
        loop = asyncio.get_event_loop()

        try:
            image_data, detected_ext = await loop.run_in_executor(
                None,
                self._generate_sync,
                client, contents, config,
            )
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(f"Gemini image generation failed: {exc}") from exc

        if detected_ext:
            suffix = detected_ext

        # Save to file
        dir_path = directory if directory else Settings.CACHE_DIR / "images"
        ensure_dir(str(dir_path))

        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=str(dir_path),
        )
        tmp.write(image_data)
        tmp.close()

        # tmp.name is an absolute path string
        image_path = dir_path / tmp.name.rsplit("/", 1)[-1]
        logger.info(f"Image saved to: {image_path} ({len(image_data) // 1024} KB)")
        return image_path

    def _generate_sync(self, client, contents, config):
        """Synchronous image generation (runs in executor thread)."""
        image_data = None
        detected_ext = None

        for chunk in client.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config=config,
        ):
            if chunk.parts is None:
                continue

            for part in chunk.parts:
                if part.inline_data and part.inline_data.data:
                    image_data = part.inline_data.data
                    mime = part.inline_data.mime_type
                    detected_ext = mimetypes.guess_extension(mime) or ".png"
                    logger.info(f"Received image data ({mime}, {len(image_data)} bytes)")
                elif part.text:
                    logger.info(f"Gemini text response: {part.text[:100]}")

        if not image_data:
            raise AIProviderError("Gemini returned no image data. The model may not support image generation for this prompt.")

        return image_data, detected_ext
