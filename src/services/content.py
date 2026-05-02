from __future__ import annotations

import os
from typing import Any

from browser.manager import Manager
from helpers.exceptions import LinkedInMCPError
from providers.base import BaseProvider
from providers.image import ImageProvider
from config import Settings, setup_logger, delete
from config.prompts import (
    CONTENT_GENERATION_SYSTEM_PROMPT,
    CONTENT_GENERATION_USER_PROMPT_TEMPLATE,
)

logger = setup_logger(Settings.LOG_DIR / "content.log", name="linkedin-mcp.services.content")

# ── Image prompt generation prompts ──────────────────────────────────────────

_IMAGE_PROMPT_SYSTEM = """You are a professional visual art director specializing in LinkedIn content.
Your task is to write a detailed, photorealistic image generation prompt for a LinkedIn post.
The image must be professional, on-brand, and visually compelling for a business audience.

Rules:
- Write ONLY the image generation prompt, nothing else.
- Be concrete and specific about visual elements, lighting, composition, and mood.
- Use descriptive keywords suitable for diffusion models (Flux, DALL-E, Stable Diffusion).
- Avoid faces, text overlays, or trademarked logos.
- Length: 60-120 words.
"""

_IMAGE_PROMPT_USER_TEMPLATE = """LinkedIn Post Topic: {topic}
Post Tone: {tone}
Post Content Summary: {post_preview}

Generate a detailed image generation prompt that visually represents this topic in a professional context."""


class ContentService:
    """Service handling interactions with LinkedIn posts and AI-powered content creation."""

    _SYSTEM_PROMPT = CONTENT_GENERATION_SYSTEM_PROMPT

    def __init__(
        self,
        browser: Manager | None = None,
        ai: BaseProvider | None = None,
        image_provider: ImageProvider | None = None,
    ) -> None:
        self.browser = browser
        self.ai = ai
        self.image_provider = image_provider

    # ── Post Interaction ─────────────────────────────────────────────────────

    async def interact_with_post(
        self,
        post_url: str,
        action: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Interact with a LinkedIn post — read, like, or comment.

        Args:
            post_url: URL of the LinkedIn post.
            action:   Action to perform ('read', 'like', 'comment').
            comment:  Text for comment action (required if action is 'comment').

        Returns:
            Dictionary with interaction results.
        """
        if not self.browser:
            raise LinkedInMCPError("Browser layer unavailable. Enable GUI auth.")

        if not ("linkedin.com/posts/" in post_url or "linkedin.com/feed/update/" in post_url):
            raise LinkedInMCPError("Invalid LinkedIn post URL provided.")

        logger.info(f"Targeting post: {post_url} with action: {action}")

        try:
            if action == "read":
                return await self.browser.read_post(post_url)
            elif action == "like":
                return await self.browser.like_post(post_url)
            elif action == "comment":
                if not comment:
                    raise LinkedInMCPError("Comment text is required for the 'comment' action.")
                return await self.browser.comment_on_post(post_url, comment)
            else:
                raise LinkedInMCPError(
                    f"Action '{action}' is not supported. Use 'read', 'like', or 'comment'."
                )
        except LinkedInMCPError:
            raise
        except Exception as exc:
            logger.error(f"Post interaction failed: {exc}")
            raise LinkedInMCPError(f"Post interaction failed: {exc}") from exc

    # ── AI-Powered Post Creation ─────────────────────────────────────────────

    async def _generate_image_prompt(
        self, topic: str, tone: str, post_preview: str
    ) -> str:
        """
        Use the main AI provider to write a detailed image generation prompt.

        This is a two-step pipeline:
            topic/tone → LLM → rich image prompt → ImageProvider → image URL

        Args:
            topic:        The LinkedIn post topic.
            tone:         Desired post tone.
            post_preview: First 300 chars of the generated post text.

        Returns:
            A detailed image generation prompt string.
        """
        if not self.ai:
            raise LinkedInMCPError("AI provider not configured — cannot generate image prompt.")

        user_prompt = _IMAGE_PROMPT_USER_TEMPLATE.format(
            topic=topic,
            tone=tone,
            post_preview=post_preview[:300],
        )

        logger.info(f"Generating image prompt for topic: '{topic[:60]}'")
        image_prompt = await self.ai.generate_text(
            system_prompt=_IMAGE_PROMPT_SYSTEM,
            user_prompt=user_prompt,
        )
        image_prompt = image_prompt.strip()
        logger.info(f"Image prompt generated ({len(image_prompt)} chars)")
        return image_prompt

    async def generate_and_submit_post(
        self,
        topic: str,
        tone: str = "professional",
        include_cta: bool = True,
        include_image: bool = False,
    ) -> dict[str, Any]:
        """
        Full pipeline: generate LinkedIn post text, optionally generate an image,
        and publish both via the browser.

        Pipeline (when include_image=True):
            1. LLM writes the post text (topic + tone + CTA).
            2. LLM writes a detailed image generation prompt (from topic + post text).
            3. ImageProvider generates the image and downloads it locally.
            4. Browser uploads image + post text together.

        Args:
            topic:         The subject for the post.
            tone:          Writing style ('professional', 'storytelling', 'thought-leader').
            include_cta:   Whether to add a call-to-action at the end.
            include_image: Whether to generate and attach an AI image.

        Returns:
            dict with status, generated_post, character_count, topic,
            and optionally image_prompt + image_url.
        """
        if not self.ai:
            raise LinkedInMCPError("AI provider not configured. Check your API keys.")
        if not self.browser:
            raise LinkedInMCPError("Browser layer unavailable. Enable GUI auth.")

        # ── Step 1: Generate post text ─────────────────────────────────────
        cta_instruction = (
            "Include a soft call-to-action or a question to spark discussion."
            if include_cta
            else "Do not include a call-to-action."
        )

        user_prompt = CONTENT_GENERATION_USER_PROMPT_TEMPLATE.format(
            topic=topic,
            tone=tone,
            cta_instruction=cta_instruction,
        )

        logger.info(f"Generating LinkedIn post for topic: '{topic[:60]}'")
        generated_text = await self.ai.generate_text(
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        logger.info(f"Post generated ({len(generated_text)} chars).")

        result: dict[str, Any] = {
            "generated_post": generated_text,
            "character_count": len(generated_text),
            "topic": topic,
        }

        image_path_obj: Any = None

        # ── Step 2 & 3: Generate image (optional) ─────────────────────────
        if include_image:
            if not self.image_provider:
                logger.warning("include_image=True but no image provider configured. Skipping.")
                result["image_warning"] = "Image generation skipped — IMAGE_GEN_API_BASE not configured."
            else:
                try:
                    # Step 2: LLM writes image prompt
                    image_prompt = await self._generate_image_prompt(
                        topic=topic,
                        tone=tone,
                        post_preview=generated_text,
                    )
                    result["image_prompt"] = image_prompt

                    # Step 3: Generate + download image
                    image_path_obj = await self.image_provider.generate_and_download(
                        prompt=image_prompt,
                        suffix=".png",
                    )
                    result["image_url"] = f"file://{image_path_obj}"
                    logger.info(f"Image ready: {image_path_obj}")

                except Exception as exc:
                    logger.error(f"Image generation failed: {exc}")
                    result["image_warning"] = f"Image generation failed: {exc}. Posting text only."
                    image_path_obj = None

        # ── Step 4: Submit to LinkedIn ─────────────────────────────────────
        try:
            browser_result = await self.browser.create_post(
                text=generated_text,
                image_path=str(image_path_obj) if image_path_obj and image_path_obj.exists() else None,
            )
        finally:
            # Always clean up the temp file
            if image_path_obj and image_path_obj.exists():
                try:
                    delete(str(image_path_obj))
                except OSError as e:
                    logger.debug(f"Failed to delete temporary image file {image_path_obj}: {e}")

        return {**result, **browser_result}


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta

SERVICE = ServiceMeta(
    attr="content",
    cls=ContentService,
    lazy=True,
    factory=lambda ctx: ContentService(
        browser=ctx.browser,
        ai=ctx.ai,
        image_provider=ctx.image_provider,
    ),
)
