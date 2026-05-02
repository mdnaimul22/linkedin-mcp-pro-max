import asyncio
from typing import Dict, Any, Optional
from patchright.async_api import Page
from browser.helpers.executor import ApiExecutor
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "content_interactor.log", name="linkedin-mcp.browser.actors.interactor")

class ContentInteractor:
    """
    LinkedIn Content Interaction Actor.
    Uses ApiExecutor for semantic, selector-free automation.
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.executor = ApiExecutor(page)

    async def comment_on_post(self, text: str) -> Dict[str, Any]:
        """Adds a comment to the currently open post semantically."""
        try:
            # Discover and fill comment editor
            discovery = await self.executor.discover()
            
            # Map "comment" or "write" to the editor
            success = await self.executor.fill_semantic_field("comment", text, discovery)
            if not success:
                success = await self.executor.fill_semantic_field("write", text, discovery)
            
            if not success:
                 return {"status": "error", "message": "Could not find comment editor semantically."}

            # Click Post/Comment button
            clicked = await self.executor.click_button("Post", discovery)
            if not clicked:
                clicked = await self.executor.click_button("Comment", discovery)
            
            if not clicked:
                return {"status": "error", "message": "Could not find submit button semantically."}

            await asyncio.sleep(2.0)
            return {
                "status": "success",
                "action": "comment",
                "message": "Comment posted successfully semantically."
            }
        except Exception as e:
            logger.error(f"Semantic comment failed: {e}")
            return {"status": "error", "message": str(e)}

    async def create_post(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Creates a new post using semantic field discovery and smart automation."""
        try:
            logger.info("Starting semantic post creation flow...")
            await self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            
            # 1. Open Post Modal
            discovery = await self.executor.discover()
            
            # Try "Start a post" or "Write post" first to avoid file picker
            trigger_labels = ["Start a post", "Write post"]
            if image_path:
                trigger_labels.insert(0, "Photo")
            else:
                trigger_labels.append("Photo") # Last resort

            trigger_success = False
            for label in trigger_labels:
                if await self.executor.click_button(label, discovery):
                    trigger_success = True
                    break
            
            if not trigger_success:
                # Fallback to coordinate-less discovery if labels fail
                logger.warning("Semantic post triggers failed, trying fallback discovery...")
                await asyncio.sleep(2)
                discovery = await self.executor.discover()

            # 2. Handle Image if provided
            if image_path:
                # Click "Add media" or "Photo" inside modal
                async with self.page.expect_file_chooser() as fc_info:
                    media_clicked = await self.executor.click_button("Add media", discovery)
                    if not media_clicked:
                        media_clicked = await self.executor.click_button("Photo", discovery)
                
                if media_clicked:
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(image_path)
                    await asyncio.sleep(2)
                    # Click "Done" or "Next"
                    await self.executor.click_button("Done")
                    await asyncio.sleep(2)

            # 3. Fill Post Content
            # Wait for modal to settle
            await asyncio.sleep(2)
            modal_discovery = await self.executor.discover()
            
            # Fill the editor (usually labeled "post", "write", or has placeholder)
            fill_success = await self.executor.smart_fill({
                "post": text,
                "write": text,
                "share": text,
                "editor": text
            }, modal_discovery)
            
            if not any(v == "success" for v in fill_success.values()):
                # Final attempt: find any large contenteditable or textarea
                logger.info("Semantic fill failed, trying broad discovery...")
                for f in (modal_discovery.textareas + modal_discovery.inputs):
                    if f.is_contenteditable or f.tag == "textarea":
                         logger.info(f"Found candidate editor: {f.tag} (id={f.id}). Filling...")
                         await self.page.locator(f"#{f.id}").first.click()
                         await self.page.locator(f"#{f.id}").first.fill(text)
                         break

            # 4. Click Post
            await asyncio.sleep(1)
            posted = await self.executor.click_button("Post")
            if not posted:
                # Direct selector fallback for LinkedIn's specific post button classes
                logger.info("Semantic 'Post' button not found, trying CSS fallbacks...")
                post_selectors = [
                    "button.share-actions__primary-action", 
                    "button.share-box-footer__primary-btn",
                    "[data-test-id='share-actions__primary-action']"
                ]
                for sel in post_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if await btn.is_visible():
                            await btn.click()
                            posted = True
                            break
                    except: continue
            
            if not posted:
                return {"status": "error", "message": "Could not find 'Post' button semantically or via fallback."}

            await asyncio.sleep(3)
            return {
                "status": "success",
                "action": "create_post",
                "message": "Post submitted successfully via semantic discovery."
            }

        except Exception as e:
            logger.error(f"Semantic post creation failed: {e}")
            failure_path = Settings.LOG_DIR / "semantic_post_failure.png"
            await self.page.screenshot(path=str(failure_path))
            return {"status": "error", "message": str(e)}

# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ActorMeta
ACTOR = ActorMeta(attr="content_interactor", cls=ContentInteractor)
