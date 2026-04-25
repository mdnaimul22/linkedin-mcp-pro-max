from __future__ import annotations

import asyncio
import logging

from browser import (
    Manager,
    validate_linkedin_auth,
    handle_login_form,
    stabilize_navigation,
)
from browser.session import Session

logger = logging.getLogger("linkedin-mcp.services.auth")


class AuthResolver:
    """Resolver for LinkedIn authentication barriers and login orchestration."""

    def __init__(
        self, browser: Manager, session_manager: Session
    ) -> None:
        self.browser = browser
        self.sessions = session_manager

    async def is_authenticated(self) -> bool:
        """Check if the current session is authenticated with LinkedIn."""
        return await validate_linkedin_auth(self.browser.page)

    async def login_automated(self, timeout: int = 120) -> bool:
        """Perform an autonomous headless login using stored credentials."""
        logger.info("Attempting autonomous headless login...")
        await self.browser.start()
        page = self.browser.page

        username = self.sessions.settings.linkedin_email
        password_secret = self.sessions.settings.linkedin_password
        if not username or not password_secret:
            logger.error("LinkedIn credentials missing in settings")
            return False
        password = password_secret.get_secret_value()

        try:
            await page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await stabilize_navigation(page, timeout=5000)

            success = await handle_login_form(page, username, password)
            if not success:
                return False

            logger.info("Login form submitted. Waiting for redirect...")

            loop = asyncio.get_running_loop()
            start_time = loop.time()
            while loop.time() - start_time < timeout:
                url = page.url
                logger.debug("Current URL: %s", url)

                if "linkedin.com/feed" in url:
                    logger.info("Successfully reached LinkedIn feed.")
                    self.sessions.write_source_state()
                    await self.browser.export_cookies()
                    return True

                if "checkpoint" in url:
                    logger.warning("Security checkpoint detected: %s", url)
                    cp_path = self.sessions.auth_root / "login-checkpoint.png"
                    await page.screenshot(path=str(cp_path))
                    logger.info("Checkpoint screenshot saved to %s", cp_path)

                await asyncio.sleep(2)

            logger.error("Automated login timed out or failed to reach feed.")
            try:
                debug_path = self.sessions.auth_root / "login-failure.png"
                await page.screenshot(path=str(debug_path))
                logger.info("Debug screenshot saved to %s", debug_path)
            except Exception as exc:
                logger.error("Failed to save debug screenshot: %s", exc)

            return False

        except Exception as exc:
            logger.error("Automated login failed: %s", exc)
            try:
                err_path = self.sessions.auth_root / "login-error.png"
                await page.screenshot(path=str(err_path))
                logger.info("Error screenshot saved to %s", err_path)
            except Exception:
                pass
            return False

    async def logout(self) -> bool:
        """Clear all stored LinkedIn profile and session artifacts."""
        try:
            success = self.sessions.logout()
            if success:
                logger.info("Logged out successfully. All profiles cleared.")
            return success
        except Exception as exc:
            logger.error("Failed to clear auth artifacts: %s", exc)
            return False
