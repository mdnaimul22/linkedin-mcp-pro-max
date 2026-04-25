from __future__ import annotations
import logging
import json
import re
from pathlib import Path
from typing import Any

from patchright.async_api import BrowserContext, Page, ViewportSize
from browser.helpers.driver import BrowserDriver
from browser.helpers import stabilize_navigation
from browser.actors.auth import validate_linkedin_auth, export_linkedin_cookies
from helpers.exceptions import AuthenticationError
from schema import SourceState

logger = logging.getLogger("linkedin-mcp.browser.manager")


class Manager:

    def __init__(self, session_manager: Any, driver: BrowserDriver) -> None:
        self.sessions = session_manager
        self.driver = driver
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self.is_authenticated: bool = False
        self._actors: dict[str, Any] = {}
        self._scrapers: dict[str, Any] = {}
        self._actor_classes: dict[str, type] = {}
        self._scraper_classes: dict[str, type] = {}
        self._cached_profile_id: str | None = None
        self.api_executor: Any = None

    async def start(self) -> None:
        if self._context:
            return
        self._context = await self.driver.start()
        self._page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )

        from helpers.registry import get_actors, get_scrapers
        for meta in get_actors():
            self._actor_classes[meta.attr] = meta.cls
        for meta in get_scrapers():
            self._scraper_classes[meta.attr] = meta.cls

        logger.info(
            "Browser manager ready — %d actor(s), %d scraper(s) registered for lazy-loading.",
            len(self._actor_classes),
            len(self._scraper_classes),
        )

    async def close(self) -> None:
        """Close browser resources."""
        self._page = None
        self._context = None
        self._actors.clear()
        self._scrapers.clear()
        self._cached_profile_id = None
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


    def set_api_executor(self, executor: Any) -> None:
        """Inject ApiExecutor into all registered scrapers.

        This is the single public entry-point for wiring the API executor.
        app.py must call this instead of directly looping over self._scrapers.
        """
        self.api_executor = executor
        # Update any already instantiated scrapers
        for scraper in self._scrapers.values():
            if hasattr(scraper, "api_executor"):
                scraper.api_executor = executor
        logger.debug("ApiExecutor ready to be wired into scrapers.")

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        actors = object.__getattribute__(self, "_actors")
        scrapers = object.__getattribute__(self, "_scrapers")
        actor_classes = object.__getattribute__(self, "_actor_classes")
        scraper_classes = object.__getattribute__(self, "_scraper_classes")
        page = object.__getattribute__(self, "_page")

        if name in actors:
            return actors[name]
        if name in scrapers:
            return scrapers[name]

        if name in actor_classes:
            if not page:
                raise RuntimeError(f"Cannot instantiate actor '{name}' before browser start.")
            actor = actor_classes[name](page)
            actors[name] = actor
            logger.debug("Lazy-loaded actor: %s", name)
            return actor

        if name in scraper_classes:
            if not page:
                raise RuntimeError(f"Cannot instantiate scraper '{name}' before browser start.")
            scraper = scraper_classes[name](page)
            
            # Inject api_executor if available
            api_executor = object.__getattribute__(self, "api_executor")
            if api_executor and hasattr(scraper, "api_executor"):
                scraper.api_executor = api_executor
                
            scrapers[name] = scraper
            logger.debug("Lazy-loaded scraper: %s", name)
            return scraper

        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'. "
            f"Available actors: {list(actor_classes)}. "
            f"Available scrapers: {list(scraper_classes)}."
        )

    async def get_current_profile_id(self) -> str:
        """Resolve the authenticated user's LinkedIn profile slug.

        Result is cached in-session — the /me navigation only runs once per session.
        """
        if self._cached_profile_id:
            return self._cached_profile_id

        logger.info("Resolving current profile ID...")

        if self.sessions.settings.linkedin_username:
            logger.debug("Using profile ID from settings: %s", self.sessions.settings.linkedin_username)
            self._cached_profile_id = self.sessions.settings.linkedin_username
            return self._cached_profile_id

        try:
            logger.debug("Resolving via /me redirect on a dedicated page...")
            temp_page = await self.page.context.new_page()
            await temp_page.goto("https://www.linkedin.com/me", wait_until="commit", timeout=30000)
            
            try:
                await temp_page.wait_for_url("**/in/**", timeout=15000)
            except Exception:
                logger.debug("URL after /me navigation: %s", temp_page.url)

            match = re.search(r"linkedin\.com/in/([^/?#]+)", temp_page.url)
            await temp_page.close()
            
            if match:
                slug = match.group(1)
                logger.info("Resolved current profile ID: %s", slug)
                self._cached_profile_id = slug
                return slug
        except Exception as e:
            logger.warning(f"Failed to resolve profile via /me redirect: {e}")
            try:
                await temp_page.close()
            except Exception:
                pass

        raise AuthenticationError("Could not resolve profile ID and no LINKEDIN_USERNAME in settings.")

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

    # --- PROFILE ---
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

    async def update_cover_image(self, image_path: str) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.update_cover_image(pid, image_path)

    # --- EXPERIENCE ---
    async def upsert_experience(self, **kwargs: Any) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.upsert_experience(profile_id=pid, **kwargs)

    async def remove_experience(self, company: str, title: str) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.remove_experience(pid, company, title)

    # --- EDUCATION ---
    async def upsert_education(self, **kwargs: Any) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.upsert_education(profile_id=pid, **kwargs)

    async def remove_education(self, school: str, degree: str) -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.remove_education(pid, school, degree)

    # --- SKILLS ---
    async def manage_skills(self, skill_name: str, action: str = "add") -> dict[str, Any]:
        pid = await self.get_current_profile_id()
        return await self.profile_editor.manage_skills(pid, skill_name, action)

    # --- POSTS / CONTENT ---
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


async def create_browser(
    session_manager: Any,
    headless: bool = True,
    cdp_url: str | None = None,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    slow_mo: int = 0,
    **launch_options: Any,
) -> Manager:
    
    viewport = ViewportSize(width=viewport_width, height=viewport_height)

    if cdp_url:
        driver = BrowserDriver(
            user_data_dir=session_manager.source_profile_dir,
            cdp_url=cdp_url,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = Manager(session_manager, driver)
        await mgr.start()
        mgr.is_authenticated = True
        return mgr

    source_state = session_manager.load_source_state()
    rid = session_manager.runtime_id

    if not source_state or not session_manager.source_profile_exists():
        driver = BrowserDriver(
            user_data_dir=session_manager.source_profile_dir,
            headless=headless,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = Manager(session_manager, driver)
        await mgr.start()
        return mgr

    if rid == source_state.source_runtime_id:
        driver = BrowserDriver(
            user_data_dir=session_manager.source_profile_dir,
            headless=headless,
            viewport=viewport,
            slow_mo=slow_mo,
            **launch_options,
        )
        mgr = Manager(session_manager, driver)
        await mgr.start()
        if await validate_linkedin_auth(mgr.page):
            mgr.is_authenticated = True
        return mgr

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
        mgr = Manager(session_manager, driver)
        await mgr.start()
        if await validate_linkedin_auth(mgr.page):
            mgr.is_authenticated = True
            return mgr

    driver = await _bridge_linkedin_session(
        sessions=session_manager,
        source_state=source_state,
        headless=headless,
        viewport=viewport,
        slow_mo=slow_mo,
        **launch_options,
    )
    mgr = Manager(session_manager, driver)
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
