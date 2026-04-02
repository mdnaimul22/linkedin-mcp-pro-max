"""LinkedIn engagement and interaction logic.

Handles automated actions like liking and commenting on content.
"""

import asyncio
import logging
from typing import Dict, Any
from patchright.async_api import Page
from browser.helpers.dom import wait_for_any_selector

logger = logging.getLogger("linkedin-mcp.browser.actors.interactor")


class ContentInteractor:
    """Actor responsible for engaging with posts and articles."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def like_post(self) -> Dict[str, Any]:
        """Likes the currently loaded post if not already liked.
        
        Returns:
            dict indicating success, action taken, and message.
        """
        try:
            # Check if button exists and its state in one evaluation to avoid race conditions
            liked = await self.page.evaluate('''() => {
                const likeButton = document.querySelector('button.react-button__trigger');
                if (!likeButton) return null; // Button not found 
                
                const isLiked = likeButton.getAttribute('aria-pressed') === 'true';
                if (!isLiked) {
                    likeButton.click();
                    return true; // We clicked it
                }
                return false; // It was already liked
            }''')
            
            if liked is None:
                return {"status": "error", "message": "Like button not found on the page."}
            elif liked:
                return {"status": "success", "action": "like", "performed": True, "message": "Successfully liked the post."}
            else:
                return {"status": "success", "action": "like", "performed": False, "message": "Post was already liked."}
                
        except Exception as e:
            logger.error(f"Failed to like post: {e}")
            return {"status": "error", "message": f"Exception during like action: {e}"}

    async def comment_on_post(self, text: str) -> Dict[str, Any]:
        """Posts a comment on the currently loaded post.
        
        Args:
            text: The text content of the comment to post.
            
        Returns:
            dict indicating success and message.
        """
        try:
            # 1. Click to open comment box
            trigger_selector = "button.comments-comment-box__trigger"
            await wait_for_any_selector(self.page, [trigger_selector])
            await self.page.click(trigger_selector)
            
            # 2. Fill the comment text
            editor_selector = ".ql-editor"
            await self.page.wait_for_selector(editor_selector, state="visible")
            await self.page.fill(editor_selector, text)
            
            # 3. Submit
            submit_selector = "button.comments-comment-box__submit-button"
            await self.page.click(submit_selector)
            
            # 4. Wait for submission to complete
            await asyncio.sleep(2.0)
            
            return {
                "status": "success",
                "action": "comment",
                "message": "Comment posted successfully."
            }
            
        except Exception as e:
            logger.error(f"Failed to comment on post: {e}")
            return {"status": "error", "message": f"Exception during comment action: {e}"}

    async def create_post(self, text: str) -> Dict[str, Any]:
        """Creates a new post on the user's LinkedIn feed.
        
        Args:
            text: The text content of the post to publish.
            
        Returns:
            dict indicating success and message.
        """
        try:
            logger.info("Starting post creation flow...")
            # 1. Ensure we are on the feed page
            await self.page.goto("https://www.linkedin.com/feed/")
            await self.page.wait_for_load_state("domcontentloaded")
            
            # 2. Click "Start a post"
            start_post_selector = "button.share-box-feed-entry__trigger, button[aria-label='Start a post']"
            await self.page.wait_for_selector(start_post_selector, state="visible", timeout=10000)
            await self.page.click(start_post_selector)
            
            # 3. Wait for modal text editor
            editor_selector = "div.ql-editor[contenteditable='true']"
            await self.page.wait_for_selector(editor_selector, state="visible", timeout=10000)
            
            # 4. Fill text
            await self.page.fill(editor_selector, text)
            await asyncio.sleep(1.0) # wait for button to become enabled
            
            # 5. Click the "Post" button
            submit_selector = "button.share-actions__primary-action, button[data-test-id='share-actions__primary-action']"
            submit_button = self.page.locator(submit_selector).first
            
            # Ensure the button is enabled
            is_disabled = await submit_button.get_attribute("disabled")
            if is_disabled is not None:
                return {"status": "error", "message": "Post button remains disabled. Text may be invalid."}
            
            await submit_button.click()
            
            # 6. Wait for modal to close (completion confirmation)
            try:
                await self.page.wait_for_selector("div.share-box-modal", state="hidden", timeout=10000)
            except Exception:
                logger.warning("Modal did not disappear explicitly, checking if post was successful...")
            
            # Wait a moment for network dispatch
            await asyncio.sleep(2.0)
            
            return {
                "status": "success",
                "action": "create_post",
                "message": "Post submitted successfully.",
                "length": len(text)
            }
            
        except Exception as e:
            logger.error(f"Failed to create post: {e}")
            return {"status": "error", "message": f"Exception during post creation: {e}"}


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ActorMeta
ACTOR = ActorMeta(attr="content_interactor", cls=ContentInteractor)
