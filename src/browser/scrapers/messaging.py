"""LinkedIn messaging and inbox scraping logic.

Handles reading chat threads, messages, and conversation history.
"""

import logging
from typing import Any
from patchright.async_api import Page

logger = logging.getLogger("linkedin-mcp.browser.scrapers.messaging")


class MessagingScraper:
    """Specialized scraper for LinkedIn inbox and messages."""

    def __init__(self, page: Page) -> None:
        self.page = page

    # TODO: Implement message extraction, inbox polling, and conversation reading.


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ScraperMeta
SCRAPER = ScraperMeta(attr="messaging_scraper", cls=MessagingScraper)
