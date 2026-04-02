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
) -> str:
    """Generate and publish a new LinkedIn post using an internal AI writer.

    The AI will craft a complete, publish-ready post based on the topic you
    provide. The post is then automatically submitted to LinkedIn via the
    authenticated browser session.

    Args:
        topic: What the post should be about. Be as specific or as broad as
               you like (e.g., 'lessons learned from 6 months of remote work',
               'why clean code matters in a startup environment').
        tone:  Writing style. Options: 'professional' (default), 'storytelling',
               'thought-leader'. Choose based on the mood you want to set.
        include_cta: If True (default), the post will end with a question or
                     call-to-action to drive engagement.

    Returns:
        JSON string with:
          - status:          'success' or 'error'
          - generated_post:  The complete text that was published.
          - character_count: Length of the published post.
          - topic:           Echo of the original topic for traceability.
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
        )
        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"create_linkedin_post failed: {e}")
        raise ToolError(str(e))

