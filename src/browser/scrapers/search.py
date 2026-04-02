"""LinkedIn global search results scraping logic.

Handles executing global search queries and paginating through results (People, Posts, Companies).
"""

import logging
from typing import Any
from patchright.async_api import Page

logger = logging.getLogger("linkedin-mcp.browser.scrapers.search")


class SearchScraper:
    """Specialized scraper for LinkedIn dynamic search engine."""

    def __init__(self, page: Page) -> None:
        self.page = page

    # TODO: Implement global search parsing, results pagination, and filter selection.


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ScraperMeta
SCRAPER = ScraperMeta(attr="search_scraper", cls=SearchScraper)
