"""Browser DOM manipulation helpers — private utilities for the browser/ module only."""

import asyncio
from typing import Literal
from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from helpers.exceptions import RateLimitError


async def get_page_content(page: Page) -> str:
    """Extract innerText from the page body."""
    try:
        content = await page.evaluate("() => document.body?.innerText || ''")
        return str(content)
    except Exception:
        return ""


async def stabilize_navigation(
    page: Page,
    *,
    timeout: float = 5000,
    wait_until: Literal["domcontentloaded", "load", "networkidle"] = "networkidle",
    retries: int = 1,
) -> bool:
    """Wait for the page to stabilize."""
    for attempt in range(retries + 1):
        try:
            await page.wait_for_load_state(
                state=wait_until if wait_until != "networkidle" else "load",
                timeout=timeout / 2,
            )
            if wait_until == "networkidle":
                try:
                    await page.wait_for_load_state(
                        state="networkidle", timeout=timeout / 2
                    )
                except PlaywrightTimeoutError:
                    pass
            return True
        except PlaywrightTimeoutError:
            if attempt < retries:
                await asyncio.sleep(1)
                continue
            return False
    return False


async def is_visible(page: Page, selector: str, timeout: float = 1000) -> bool:
    try:
        return await page.locator(selector).is_visible(timeout=timeout)
    except Exception:
        return False


async def wait_for_any_selector(
    page: Page, selectors: list[str], timeout: float = 5000
) -> str | None:
    if not selectors:
        return None
    tasks = [
        page.wait_for_selector(sel, state="attached", timeout=timeout)
        for sel in selectors
    ]
    try:
        done, pending = await asyncio.wait(
            [asyncio.create_task(t) for t in tasks], return_when=asyncio.FIRST_COMPLETED
        )
        for p in pending:
            p.cancel()
        for task in done:
            try:
                element = await task
                if element:
                    for sel in selectors:
                        if await page.locator(sel).count() > 0:
                            return sel
            except Exception:
                continue
    except Exception:
        pass
    return None


async def detect_rate_limit(page: Page) -> None:
    if "linkedin.com/checkpoint" in page.url or "authwall" in page.url:
        raise RateLimitError(
            "LinkedIn security checkpoint detected.", suggested_wait_time=30
        )
    try:
        if await page.locator("main").count() > 0:
            return
        body_text = await page.locator("body").inner_text(timeout=1000)
        if body_text and any(
            p in body_text.lower()
            for p in ["too many requests", "rate limit", "slow down"]
        ):
            raise RateLimitError("Rate limit message detected.", suggested_wait_time=30)
    except (RateLimitError, PlaywrightTimeoutError):
        raise


async def scroll_to_bottom(
    page: Page, pause_time: float = 1.0, max_scrolls: int = 10
) -> None:
    for i in range(max_scrolls):
        prev = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(pause_time)
        if await page.evaluate("document.body.scrollHeight") == prev:
            break


async def handle_modal_close(page: Page) -> bool:
    try:
        close = page.locator(
            'button[aria-label="Dismiss"], button[aria-label="Close"], button.artdeco-modal__dismiss'
        ).first
        if await close.is_visible(timeout=1000):
            await close.click()
            await asyncio.sleep(0.5)
            return True
    except Exception:
        pass
    return False


async def scroll_job_sidebar(
    page: Page, pause_time: float = 1.0, max_scrolls: int = 10
) -> None:
    """Scroll the job search sidebar to load all job cards."""
    try:
        await page.wait_for_selector('a[href*="/jobs/view/"]', timeout=3000)
        for _ in range(max_scrolls):
            scrolled = await page.evaluate("""
                () => {
                    const el = document.querySelector('.jobs-search-results-list') || 
                               document.querySelector('div[id*="results-list"]');
                    if (el) {
                        el.scrollTop = el.scrollHeight;
                        return true;
                    }
                    return false;
                }
            """)
            if not scrolled:
                break
            await asyncio.sleep(pause_time)
    except Exception:
        pass
