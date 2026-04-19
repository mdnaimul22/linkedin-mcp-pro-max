"""MCP Tools for LinkedIn content and feed interaction."""

import json
import logging
from typing import Optional

from fastmcp.exceptions import ToolError
from app import get_ctx, mcp

logger = logging.getLogger("linkedin-mcp.tools.content")


@mcp.tool()
async def interact_with_post(
    post_url: str,
    action: str = "read",
    comment: Optional[str] = None
) -> str:
    """Interact with a specific LinkedIn post (read, like, comment).
    
    Args:
        post_url: The URL of the LinkedIn post to interact with.
        action: Strategy to apply: 'read', 'like', or 'comment'. Default is 'read'.
        comment: The text to post if action is 'comment'.
    """
    valid_actions = ["read", "like", "comment"]
    if action not in valid_actions:
        raise ToolError(f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
        
    if action == "comment" and not comment:
        raise ToolError("You must provide the 'comment' text parameter when action is 'comment'.")

    try:
        ctx = await get_ctx()
        
        # Ensure browser is initialized for these operations
        await ctx.initialize_browser()
        
        result = await ctx.content.interact_with_post(
            post_url=post_url, 
            action=action, 
            comment=comment
        )
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Post interaction failed: {e}")
        raise ToolError(str(e))


@mcp.tool()
async def create_linkedin_post(
    topic: str,
    tone: str = "professional",
    include_cta: bool = True,
    include_image: bool = False,
) -> str:
    """Generate and publish a new LinkedIn post using an internal AI writer.

    The AI will craft a complete, publish-ready post based on the topic you
    provide. Optionally, a second AI pass generates a detailed visual prompt
    which is sent to the image generation engine to create and attach a
    professional image to the post.

    Full pipeline (when include_image=True):
        1. LLM writes the post text (topic + tone + optional CTA).
        2. LLM writes a rich, detailed image generation prompt.
        3. Image generator (Flux / Gemini) creates the image.
        4. Browser uploads image + posts text together on LinkedIn.

    Args:
        topic:         What the post should be about (e.g., 'why clean code
                       matters', 'lessons from 6 months of remote work').
        tone:          Writing style — 'professional' (default), 'storytelling',
                       or 'thought-leader'.
        include_cta:   If True (default), end with a question or call-to-action.
        include_image: If True, generate and attach an AI image to the post.
                       Requires IMAGE_GEN_API_BASE to be configured. If image
                       generation fails, the post is published text-only.

    Returns:
        JSON string with:
          - status:          'success' or 'error'
          - generated_post:  The complete text that was published.
          - character_count: Length of the published post.
          - topic:           Echo of the original topic for traceability.
          - image_prompt:    (if include_image) The prompt used for image gen.
          - image_url:       (if include_image) Local path of the generated image.
          - image_warning:   (if include_image failed) Reason why image was skipped.
          - message:         Human-readable confirmation.
    """
    if not topic or not topic.strip():
        raise ToolError("A topic is required to generate a post.")

    valid_tones = ["professional", "storytelling", "thought-leader"]
    if tone not in valid_tones:
        raise ToolError(
            f"Invalid tone '{tone}'. Choose from: {', '.join(valid_tones)}"
        )

    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()

        result = await ctx.content.generate_and_submit_post(
            topic=topic,
            tone=tone,
            include_cta=include_cta,
            include_image=include_image,
        )
        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error("create_linkedin_post failed: %s", e)
        raise ToolError(str(e))

