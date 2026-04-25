from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from patchright.async_api import (
    BrowserContext,
    Playwright,
    ViewportSize,
    async_playwright,
)

from helpers.exceptions import NetworkError

logger = logging.getLogger("linkedin-mcp.browser.driver")


class BrowserDriver:
    """Manages a single Playwright browser context lifecycle.

    Supports persistent user-data-dir profiles and CDP remote connections.
    """

    def __init__(
        self,
        user_data_dir: str | Path,
        headless: bool = True,
        slow_mo: int = 0,
        viewport: ViewportSize | None = None,
        user_agent: str | None = None,
        proxy: dict[str, str] | None = None,
        cdp_url: str | None = None,
        **launch_options: Any,
    ) -> None:
        self.user_data_dir = str(Path(user_data_dir).expanduser())
        self.headless = headless
        self.slow_mo = slow_mo
        self.viewport: ViewportSize | None = viewport or ViewportSize(
            width=1280, height=720
        )
        self.user_agent = user_agent
        self.proxy = proxy
        self.cdp_url = cdp_url
        self.launch_options = launch_options

        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> BrowserContext:
        """Launch the browser (or connect via CDP) and return the context."""
        if self._context:
            return self._context

        try:
            self._playwright = await async_playwright().start()

            if self.cdp_url:
                logger.info("Connecting to system browser via CDP: %s", self.cdp_url)
                browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
                if not browser.contexts:
                    self._context = await browser.new_context(
                        viewport=self.viewport,
                        user_agent=self.user_agent,
                    )
                else:
                    self._context = browser.contexts[0]
                logger.info("Connected to CDP browser successfully")
                return self._context

            # Ensure the user data directory exists with restrictive permissions
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True, mode=0o700)

            context_options: dict[str, Any] = {
                "headless": self.headless,
                "slow_mo": self.slow_mo,
                "viewport": self.viewport,
                "proxy": self.proxy,
                **self.launch_options,
            }
            if self.user_agent:
                context_options["user_agent"] = self.user_agent

            # Patchright Chromium is stealthier than standard Chromium
            self._context = await self._playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                **context_options,
            )
            logger.info(
                "Stealth browser launched (headless=%s, user_data_dir=%s)",
                self.headless,
                self.user_data_dir,
            )
            return self._context

        except Exception as exc:
            await self.stop()
            raise NetworkError(f"Failed to launch browser: {exc}") from exc

    async def stop(self) -> None:
        """Close the browser context and stop Playwright gracefully."""
        if self._context:
            try:
                await self._context.close()
            except Exception as exc:
                logger.debug("Error closing context: %s", exc)
            self._context = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as exc:
                logger.debug("Error stopping playwright: %s", exc)
            self._playwright = None

        logger.info("Browser stopped")

    async def export_storage_state(
        self, path: str | Path, indexed_db: bool = True
    ) -> bool:
        """Export full browser storage state (cookies + localStorage) to a JSON file."""
        if not self._context:
            return False
        try:
            await self._context.storage_state(path=str(path), indexed_db=indexed_db)
            return True
        except Exception as exc:
            logger.error("Failed to export storage state: %s", exc)
            return False
