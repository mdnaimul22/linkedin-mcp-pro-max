from typing import Any, Dict
from patchright.async_api import Page
from browser.helpers.dom import wait_for_any_selector
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "feed_scraper.log", name="browser.scrapers.feed")


class FeedScraper:
    """Specialized scraper for home feed and posts."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def read_post(self) -> Dict[str, Any]:
        """Extract information from a currently loaded post page.
        
        Returns:
            dict with author, content, and engagementCount
        """
        # Wait for the main post wrapper to appear
        await wait_for_any_selector(self.page, [".feed-shared-update-v2"])
        
        # Extract content securely via JS evaluator
        post_content = await self.page.evaluate('''() => {
            const post = document.querySelector('.feed-shared-update-v2');
            if (!post) return null;
            return {
                author: post.querySelector('.feed-shared-actor__name')?.innerText?.trim() || 'Unknown',
                content: post.querySelector('.feed-shared-text')?.innerText?.trim() || '',
                engagementCount: post.querySelector('.social-details-social-counts__reactions-count')?.innerText?.trim() || '0'
            };
        }''')
        
        if not post_content:
            logger.warning("Post wrapper found but evaluation returned no content.")
            return {
                "author": "Unknown",
                "content": "",
                "engagementCount": "0"
            }
            
        return post_content


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ScraperMeta
SCRAPER = ScraperMeta(attr="feed_scraper", cls=FeedScraper)
