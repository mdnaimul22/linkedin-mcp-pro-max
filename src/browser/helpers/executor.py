"""
Universal Field Discovery Engine
Analyze any page to discover all interactive input fields,
providing a structured map of all form elements: inputs, textareas, selects, buttons.

Example URLs:
    https://www.google.com/
    https://jsontotable.org/test-api
"""

import asyncio
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag
from patchright.async_api import Page
from schema import FieldInfo, DiscoveryResult
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "browser.log", name="linkedin-mcp.browser.executor")



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Tags we care about — extensible without touching core logic
_DISCOVERABLE_TAGS: list[str] = ["input", "textarea", "select", "button", "[contenteditable='true']"]

_PAGE_LOAD_SETTLE_SECONDS: float = 3.0  # JS-heavy SPAs need time to render


def _resolve_label(tag: Tag, soup: BeautifulSoup) -> Optional[str]:
    """Resolve a human-readable label for a field via multiple fallback strategies.

    Priority chain:
        1. <label for="field-id">
        2. Wrapping <label> ancestor
        3. aria-label attribute
        4. placeholder attribute
    """
    field_id: Optional[str] = tag.get("id")

    if field_id:
        label_tag = soup.find("label", attrs={"for": field_id})
        if label_tag:
            return label_tag.get_text(strip=True) or None

    parent_label = tag.find_parent("label")
    if parent_label:
        return parent_label.get_text(strip=True) or None

    aria = tag.get("aria-label")
    if aria:
        return str(aria).strip() or None

    placeholder = tag.get("placeholder")
    if placeholder:
        return str(placeholder).strip() or None

    return None


def _extract_field(tag: Tag, soup: BeautifulSoup) -> FieldInfo:
    """Extract a normalised FieldInfo from any discoverable tag."""
    return FieldInfo(
        tag=tag.name,
        type=tag.get("type") or None,
        id=tag.get("id") or None,
        name=tag.get("name") or None,
        placeholder=tag.get("placeholder") or None,
        value=tag.get("value") or None,
        aria_label=tag.get("aria-label") or None,
        required=tag.has_attr("required"),
        disabled=tag.has_attr("disabled"),
        is_contenteditable=tag.get("contenteditable") == "true",
        label=_resolve_label(tag, soup),
        selector=f"#{tag.get('id')}" if tag.get("id") else None
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ApiExecutor:
    def __init__(self, page: Page, **kwargs: Any) -> None:
        self._page = page
        self._registry_path: Optional[str] = kwargs.get("registry_path")

    async def execute(self, url: str) -> DiscoveryResult:
        """Navigate to a URL and return a structured map of all discovered input fields."""
        logger.info(f"Field Discovery Engine: navigating to {url}")
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(_PAGE_LOAD_SETTLE_SECONDS)
            return await self.discover(url)
        except Exception as exc:
            logger.error(f"Field discovery failed at {url}: {exc}")
            return DiscoveryResult(url=url, success=False, error=str(exc))

    async def discover(self, url: Optional[str] = None) -> DiscoveryResult:
        """Analyze the current page and return a structured map of all discovered input fields."""
        current_url = url or self._page.url
        logger.info(f"Field Discovery Engine: analyzing current page {current_url}")

        try:
            html = await self._page.content()
            soup = BeautifulSoup(html, "lxml")

            result = DiscoveryResult(url=current_url)

            for tag in soup.select(", ".join(_DISCOVERABLE_TAGS)):
                field = _extract_field(tag, soup)

                if tag.name == "input":
                    result.inputs.append(field)
                elif tag.name == "textarea" or tag.get("contenteditable") == "true":
                    result.textareas.append(field)
                elif tag.name == "select":
                    result.selects.append(field)
                elif tag.name == "button":
                    result.buttons.append(field)

            result.rebuild_summary()
            return result

        except Exception as exc:
            logger.error(f"Field discovery failed: {exc}")
            return DiscoveryResult(url=current_url, success=False, error=str(exc))

    # --- Robust Automation & Self-Healing Methods ---

    async def smart_fill(self, field_data: dict[str, Any], discovery: Optional[DiscoveryResult] = None) -> dict[str, str]:
        """
        Intelligently fill multiple fields based on semantic matching.
        Eliminates the need for hardcoded selectors in actors.
        """
        if not discovery:
            discovery = await self.discover()

        results = {}
        for key, value in field_data.items():
            if not value: continue
            success = await self.fill_semantic_field(key, str(value), discovery)
            results[key] = "success" if success else "failed"
            
        return results

    async def fill_semantic_field(self, key: str, value: str, discovery: DiscoveryResult) -> bool:
        """Find the best matching input/textarea for a key and fill it."""
        all_fields = discovery.inputs + discovery.textareas
        
        # Priority 1: Label match
        target = next((f for f in all_fields if f.label and key.lower() in f.label.lower()), None)
        
        # Priority 2: Placeholder match
        if not target:
            target = next((f for f in all_fields if f.placeholder and key.lower() in f.placeholder.lower()), None)
        
        # Priority 3: ID/Name suffix match (common in LinkedIn)
        if not target:
            target = next((f for f in all_fields if (f.id and f.id.lower().endswith(f"-{key.lower()}")) or 
                                               (f.name and f.name.lower().endswith(f"-{key.lower()}"))), None)

        if target:
            selector = target.selector or (f"#{target.id}" if target.id else None)
            if not selector:
                # Fallback to tag + placeholder/name if no ID or selector
                if target.placeholder:
                    selector = f'{target.tag}[placeholder="{target.placeholder}"]'
                elif target.name:
                    selector = f'{target.tag}[name="{target.name}"]'
                else:
                    return False # Truly anonymous field

            try:
                # Ensure the element is visible and interactive
                locator = self._page.locator(selector).first
                await locator.scroll_into_view_if_needed()
                await locator.click() # Focus first
                await locator.fill(value)
                return True
            except Exception as e:
                logger.warning(f"Failed to fill semantic field '{key}': {e}")
        
        return False

    async def click_button(self, label_query: str, discovery: Optional[DiscoveryResult] = None) -> bool:
        """Find a button semantically by label, aria-label, or text and click it."""
        if not discovery:
            discovery = await self.discover()
            
        # 1. Check discovered buttons
        for b in discovery.buttons:
            if b.label and label_query.lower() in b.label.lower():
                try:
                    locator = self._page.locator(f"#{b.id}").first
                    await locator.scroll_into_view_if_needed()
                    await locator.click()
                    return True
                except Exception as e:
                    logger.debug(f"Failed to click button with id {b.id}: {e}")
                
        # 2. Direct locator fallback for text
        try:
            btn = self._page.locator(f'button:has-text("{label_query}"), [role="button"]:has-text("{label_query}")').first
            if await btn.is_visible():
                await btn.click()
                return True
        except Exception as e:
            logger.debug(f"Failed to click button by text '{label_query}': {e}")
        
        return False

    async def select_by_label(self, label_query: str, option_label: str, discovery: Optional[DiscoveryResult] = None) -> bool:
        """Find a select element by label and select an option."""
        if not discovery:
            discovery = await self.discover()
            
        target = next((f for f in discovery.selects if f.label and label_query.lower() in f.label.lower()), None)
        
        if target and target.id:
            try:
                await self._page.locator(f"#{target.id}").select_option(label=option_label)
                return True
            except Exception as e:
                logger.warning(f"Failed to select option '{option_label}' for '{label_query}': {e}")
        
        return False

# Export ActionExecutor for forward compatibility
ActionExecutor = ApiExecutor