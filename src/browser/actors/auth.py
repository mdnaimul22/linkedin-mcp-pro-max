import asyncio
import json
from typing import Any
from patchright.async_api import Page, BrowserContext

from browser.helpers import wait_for_any_selector, stabilize_navigation
from helpers import secure_write_text
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "browser_auth.log", name="browser.actors.auth")


async def handle_login_form(page: Page, username: str, password: str) -> bool:
    """Automate interaction with the login form."""
    try:
        if "linkedin.com/feed" in page.url:
            logger.info("Already logged in (redirected to feed)")
            return True

        username_selectors = [
            "#username",
            'input[name="session_key"]',
            'input[id="username"]',
            'input[type="text"]',
            'input[autocomplete="username"]',
        ]
        password_selectors = [
            "#password",
            'input[name="session_password"]',
            'input[id="password"]',
            'input[type="password"]',
            'input[autocomplete="current-password"]',
        ]
        submit_selectors = [
            'button[type="submit"]',
            ".login__form_action_container button",
            ".btn__primary--large",
            'button[aria-label="Sign in"]',
            'button[data-litms-control-urn="login-submit"]',
        ]

        user_sel = await wait_for_any_selector(page, username_selectors, timeout=15000)
        if not user_sel:
            logger.error(f"Could not find username field. Current URL: {page.url}")
            return False

        pass_sel = await wait_for_any_selector(page, password_selectors, timeout=5000)
        if not pass_sel:
            logger.error("Could not find password field")
            return False

        await page.locator(user_sel).click()
        await page.locator(user_sel).fill("")
        await page.type(user_sel, username, delay=150)

        await page.locator(pass_sel).click()
        await page.locator(pass_sel).fill("")
        await page.type(pass_sel, password, delay=150)

        submit_sel = await wait_for_any_selector(page, submit_selectors, timeout=5000)
        if submit_sel:
            await asyncio.sleep(1)
            await page.click(submit_sel)
            return True
        else:
            logger.error("Could not find submit button")
            return False

    except Exception as exc:
        logger.error(f"Error handling login form: {exc}")
        return False


async def validate_linkedin_auth(page: Page) -> bool:
    """Check if the current page is authenticated."""
    try:
        if "linkedin.com/feed" not in page.url:
            await page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await stabilize_navigation(page)

        url = page.url
        if any(x in url for x in ["checkpoint", "authwall", "login"]):
            logger.info(f"Auth barrier detected: {url}")
            return False

        success_selectors = [
            ".global-nav",
            "#global-nav",
            ".feed-container",
            'button[aria-label="Home"]',
            'a[href="/feed/"]',
        ]
        for sel in success_selectors:
            if await page.locator(sel).count() > 0:
                logger.debug(f"Auth validated via selector: {sel}")
                return True

        if "linkedin.com/feed" in url:
            logger.debug("Auth validated via URL existence (no barrier)")
            return True

        logger.debug(f"Auth validation failed. URL: {url}")
        return False
    except Exception as exc:
        logger.debug(f"Auth validation probe failed: {exc}")
        return False


async def export_linkedin_cookies(context: BrowserContext, path: Any) -> bool:
    """Slice cookies from context and save to portable file."""
    try:
        all_cookies = await context.cookies()
        linkedin_cookies = [
            c for c in all_cookies if "linkedin.com" in c.get("domain", "")
        ]
        secure_write_text(path, json.dumps(linkedin_cookies, indent=2))
        logger.info(f"Exported {len(linkedin_cookies)} LinkedIn cookies to {path}")
        return True
    except Exception as exc:
        logger.error(f"Failed to export cookies: {exc}")
        return False
