"""Service for handling content and feed interactions."""

import logging
from typing import Any, Dict

from browser.manager import BrowserManager
from helpers.exceptions import LinkedInMCPError
from providers.base import BaseProvider
from config.prompts import (
    CONTENT_GENERATION_SYSTEM_PROMPT,
    CONTENT_GENERATION_USER_PROMPT_TEMPLATE,
)

logger = logging.getLogger("linkedin-mcp.services.content")


class ContentService:
    """Service handling interactions with LinkedIn posts and content."""

    def __init__(
        self,
        browser: BrowserManager | None = None,
        ai: BaseProvider | None = None,
    ) -> None:
        self.browser = browser
        self.ai = ai

    async def interact_with_post(
        self,
        post_url: str,
        action: str,
        comment: str | None = None
    ) -> Dict[str, Any]:
        """Interact with a specific LinkedIn post (read, like, comment).
        
        Args:
            post_url: URL of the post.
            action: Action to perform ('read', 'like', 'comment').
            comment: Text for comment (required if action is 'comment').
            
        Returns:
            Dictionary with interaction results.
        """
        if not self.browser:
            raise LinkedInMCPError("Browser layer unavailable. Enable GUI auth.")
            
        if not ('linkedin.com/posts/' in post_url or 'linkedin.com/feed/update/' in post_url):
            raise LinkedInMCPError("Invalid LinkedIn post URL provided.")
            
        if not self.browser.is_authenticated:
            # Although the browser context may be restored with cookies, it's safe to ensure
            logger.warning("Browser may not be fully authenticated.")

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
                raise LinkedInMCPError(f"Action '{action}' is not supported. Use 'read', 'like', or 'comment'.")
                
        except Exception as e:
            logger.error(f"Post interaction failed: {e}")
            raise LinkedInMCPError(f"Post interaction failed: {e}")

    # --- AI-Powered Post Creation ---

    _SYSTEM_PROMPT = CONTENT_GENERATION_SYSTEM_PROMPT

    async def generate_and_submit_post(
        self,
        topic: str,
        tone: str = "professional",
        include_cta: bool = True,
    ) -> Dict[str, Any]:
        """Generate a LinkedIn post via internal AI and publish it via the browser.

        Args:
            topic: The subject or instruction for the post (e.g., 'lessons from remote work').
            tone: Desired writing style ('professional', 'storytelling', 'thought-leader').
            include_cta: Whether to include a call-to-action at the end.

        Returns:
            dict with status, the generated post text, and character count.
        """
        if not self.ai:
            raise LinkedInMCPError("AI provider not configured. Check your API keys.")
        if not self.browser:
            raise LinkedInMCPError("Browser layer unavailable. Enable GUI auth.")

        cta_instruction = (
            "Include a soft call-to-action or a question to spark discussion."
            if include_cta
            else "Do not include a call-to-action."
        )

        user_prompt = CONTENT_GENERATION_USER_PROMPT_TEMPLATE.format(
            topic=topic,
            tone=tone,
            cta_instruction=cta_instruction
        )

        logger.info(f"Generating LinkedIn post for topic: '{topic[:60]}...'")

        try:
            generated_text = await self.ai.generate_text(
                system_prompt=self._SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise LinkedInMCPError(f"AI generation failed: {e}")

        logger.info(f"Post generated ({len(generated_text)} chars). Submitting to LinkedIn...")

        result = await self.browser.create_post(generated_text)

        return {
            **result,
            "generated_post": generated_text,
            "character_count": len(generated_text),
            "topic": topic,
        }


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="content",
    cls=ContentService,
    deps=['browser', 'ai'],
    lazy=True,
)
