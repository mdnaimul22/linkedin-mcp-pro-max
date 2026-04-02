"""Manages the LinkedIn browser session lifecycle and delegates tasks to scrapers/actors.

Architecture Note
-----------------
Actors and Scrapers are auto-discovered via `helpers.registry` and instantiated
in `start()`. No manual imports or field declarations are needed when adding new
actors or scrapers — simply place a file in `browser/actors/` or `browser/scrapers/`
and add a convention marker at the bottom.

Access pattern:
    manager.profile_editor.update_headline(...)   # actor
    manager.profile_scraper.scrape(...)            # scraper
"""

from __future__ import annotations
import logging
import json
import re
from pathlib import Path
from typing import Any

from patchright.async_api import BrowserContext, Page, ViewportSize

from browser.helpers.driver import BrowserDriver
from browser.helpers.sniffer import NetworkSniffer
from browser.helpers import stabilize_navigation
from browser.actors.auth import validate_linkedin_auth, export_linkedin_cookies
from helpers.exceptions import AuthenticationError
from schema.session import SourceState

logger = logging.getLogger("linkedin-mcp.browser.manager")


class BrowserManager:
    """Orchestrator for LinkedIn browser automation.

    Actors and scrapers are registered automatically via the component registry.
    Access them as named attributes:
        self.browser.profile_editor.update_headline(...)
        self.browser.profile_scraper.scrape(...)
    """

    def __init__(self, session_manager: Any, driver: BrowserDriver) -> None:
        self.sessions = session_manager
        self.driver = driver
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self.is_authenticated: bool = False
        self.sniffer = NetworkSniffer()

        # Dynamic actor/scraper registries (populated in start())
        self._actors: dict[str, Any] = {}
        self._scrapers: dict[str, Any] = {}

    async def start(self) -> None:
        """Initialize browser context, then auto-register all actors and scrapers."""
        if self._context:
            return
        self._context = await self.driver.start()
        self._context.on("request", self.sniffer.on_request)
        self._context.on("response", self.sniffer.on_response)
        self._page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )

        # Auto-instantiate all registered actors and scrapers
        from helpers.registry import get_actors, get_scrapers
        for meta in get_actors():
            self._actors[meta.attr] = meta.cls(self._page)
            logger.debug("Loaded actor: %s", meta.attr)
        for meta in get_scrapers():
            self._scrapers[meta.attr] = meta.cls(self._page)
            logger.debug("Loaded scraper: %s", meta.attr)

        logger.info(
            "Browser manager ready — %d actor(s), %d scraper(s).",
            len(self._actors),
            len(self._scrapers),
        )

    async def close(self) -> None:
        """Close browser resources."""
        self._page = None
        self._context = None
        self._actors.clear()
        self._scrapers.clear()
        await self.driver.stop()

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        if not self._context:
            raise RuntimeError("Browser context not initialized.")
        return self._context

    def toggle_sniffing(self, enabled: bool) -> None:
        self.sniffer.enable(enabled)

    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access to registered actors and scrapers.

        This enables direct access like:
            manager.profile_editor.update_headline(...)
            manager.profile_scraper.scrape(...)
        """
        # Avoid infinite recursion on internal dunder attributes
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        actors = object.__getattribute__(self, "_actors")
        scrapers = object.__getattribute__(self, "_scrapers")

        if name in actors:
            return actors[name]
        if name in scrapers:
            return scrapers[name]
        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'. "
            f"Available actors: {list(actors)}. "
            f"Available scrapers: {list(scrapers)}."
        )

    # ── Auth & Session Helpers ──────────────────────────────────────────────

    async def get_current_profile_id(self) -> str:
        """Resolve current UID from multiple strategies."""
        logger.info("Resolving current profile ID...")
        selectors = [
            "a.global-nav__primary-link[href*='/in/']",
            ".identity-block__link",
            ".feed-identity-module__actor-link",
            "a[href*='/in/']",
        ]

        for selector in selectors:
            count = await self.page.locator(selector).count()
            for i in range(count):
                link = self.page.locator(selector).nth(i)
                href = await link.get_attribute("href")
                if href and "/in/" in href:
                    match = re.search(r"/in/([^/?#]+)", href)
                    if match and match.group(1) not in [
                        "search", "settings", "me", "discover",
                    ]:
                        return match.group(1)

        if "linkedin.com/feed" not in self.page.url:
            await self.page.goto(
                "https://www.linkedin.com/feed/", wait_until="domcontentloaded"
            )
            await stabilize_navigation(self.page)

        await self.page.goto("https://www.linkedin.com/me", wait_until="load")
        match = re.search(r"linkedin\.com/in/([^/?#]+)", self.page.url)
        if match:
            return match.group(1)

        raise AuthenticationError("Could not resolve profile ID")

    async def export_cookies(self, path: Path | None = None) -> bool:
        target = path or self.sessions.portable_cookies_path
        return await export_linkedin_cookies(self._context, target)

    async def import_cookies(self, path: Path | None = None) -> bool:
        target = path or self.sessions.portable_cookies_path
        if not target.exists():
            return False
        try:
            cookies = json.loads(target.read_text())
            await self._context.add_cookies(cookies)
            return True
        except Exception:
            return False

    # ── Convenience Proxies (backwards-compatible) ──────────────────────────
    # These thin wrappers preserve the existing public API for services
    # that call browser methods directly. New code should access actors/scrapers
    # directly via manager.<actor_attr>.<method>(...)

    async def scrape_profile_by_id(self, profile_id: str) -> dict[str, Any]:
        """Scrape raw profile data. Mapping is caller's responsibility."""
        return await self.profile_scraper.scrape(profile_id)

    async def scrape_current_profile(self) -> dict[str, Any]:
        """Scrape current user's raw profile data."""
        profile_id = await self.get_current_profile_id()
        return await self.scrape_profile_by_id(profile_id)

    async def update_profile_headline(self, headline: str) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.update_headline(pid, headline)

    async def update_profile_summary(self, summary: str) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.update_summary(pid, summary)

    async def upsert_experience(self, **kwargs: Any) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.upsert_experience(profile_id=pid, **kwargs)

    async def remove_experience(self, company: str, title: str) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.remove_experience(pid, company, title)

    async def manage_skills(self, skill_name: str, action: str = "add") -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.manage_skills(pid, skill_name, action)

    async def read_post(self, post_url: str) -> dict[str, Any]:
        await self.page.goto(post_url, wait_until="domcontentloaded")
        await stabilize_navigation(self.page)
        return await self.feed_scraper.read_post()

    async def like_post(self, post_url: str) -> dict[str, Any]:
        await self.page.goto(post_url, wait_until="domcontentloaded")
        await stabilize_navigation(self.page)
        return await self.content_interactor.like_post()

    async def comment_on_post(self, post_url: str, text: str) -> dict[str, Any]:
        await self.page.goto(post_url, wait_until="domcontentloaded")
        await stabilize_navigation(self.page)
        return await self.content_interactor.comment_on_post(text)

    async def create_post(self, text: str) -> dict[str, Any]:
        return await self.content_interactor.create_post(text)


# ── Factory ────────────────────────────────────────────────────────────────────


async def create_browser(
    session_manager: Any,
    headless: bool = True,
    cdp_url: str | None = None,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    slow_mo: int = 0,
    **launch_options: Any,
) -> BrowserManager:
    """Create and return a fully initialized BrowserManager instance.

    Caching/singleton logic is the caller's responsibility (see AppContext).
    """
    viewport = ViewportSize(width=viewport_width, height=viewport_height)

    # CASE 1: CDP connection
    if cdp_url:
        driver = BrowserDriver(
            user_data_dir=session_manager.source_profile_dir,
            cdp_url=cdp_url,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = BrowserManager(session_manager, driver)
        await mgr.start()
        mgr.is_authenticated = True
        return mgr

    source_state = session_manager.load_source_state()
    rid = session_manager.runtime_id

    # CASE 2: No prior login state
    if not source_state or not session_manager.source_profile_exists():
        driver = BrowserDriver(
            user_data_dir=session_manager.source_profile_dir,
            headless=headless,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = BrowserManager(session_manager, driver)
        await mgr.start()
        return mgr

    # CASE 3: Same environment as source
    if rid == source_state.source_runtime_id:
        driver = BrowserDriver(
            user_data_dir=session_manager.source_profile_dir,
            headless=headless,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = BrowserManager(session_manager, driver)
        await mgr.start()
        if await validate_linkedin_auth(mgr.page):
            mgr.is_authenticated = True
        return mgr

    # CASE 4: Different environment with valid bridged session
    runtime_state = session_manager.load_runtime_state(rid)
    if (
        runtime_state
        and runtime_state.source_login_generation == source_state.login_generation
        and Path(runtime_state.profile_path).exists()
    ):
        driver = BrowserDriver(
            user_data_dir=runtime_state.profile_path,
            headless=headless,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = BrowserManager(session_manager, driver)
        await mgr.start()
        if await validate_linkedin_auth(mgr.page):
            mgr.is_authenticated = True
            return mgr

    # CASE 5: Build new bridged session
    driver = await _bridge_linkedin_session(
        sessions=session_manager,
        source_state=source_state,
        headless=headless,
        viewport=viewport,
        slow_mo=slow_mo,
        **launch_options,
    )
    mgr = BrowserManager(session_manager, driver)
    await mgr.start()
    mgr.is_authenticated = True
    return mgr


async def _bridge_linkedin_session(
    sessions: Any,
    source_state: SourceState,
    headless: bool = True,
    viewport: ViewportSize | None = None,
    slow_mo: int = 0,
    **launch_options: Any,
) -> BrowserDriver:
    """Bridge from source cookies to a new runtime-specific profile."""
    rid = sessions.runtime_id
    derived_dir = sessions.get_runtime_profile_dir(rid)
    storage_state_path = sessions.get_runtime_storage_state_path(rid)
    portable_cookies_path = sessions.portable_cookies_path

    sessions.clear_runtime(rid)
    bridge_driver = BrowserDriver(
        user_data_dir=derived_dir,
        headless=headless,
        viewport=viewport,
        slow_mo=slow_mo,
        **launch_options,
    )

    try:
        context = await bridge_driver.start()
        if not portable_cookies_path.exists():
            raise AuthenticationError("Source cookies missing")

        cookies = json.loads(portable_cookies_path.read_text())
        await context.add_cookies(cookies)

        page = context.pages[0] if context.pages else await context.new_page()
        if not await validate_linkedin_auth(page):
            raise AuthenticationError("Cookies expired")

        await bridge_driver.export_storage_state(storage_state_path)
        await bridge_driver.stop()

        final_driver = BrowserDriver(
            user_data_dir=derived_dir,
            headless=headless,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        final_context = await final_driver.start()
        final_page = (
            final_context.pages[0]
            if final_context.pages
            else await final_context.new_page()
        )

        if not await validate_linkedin_auth(final_page):
            raise AuthenticationError("Validation failed after bridge")

        sessions.write_runtime_state(
            source_state=source_state,
            storage_state_path=storage_state_path,
            runtime_id=rid,
        )
        await final_driver.stop()
        return final_driver
    except Exception:
        await bridge_driver.stop()
        raise
