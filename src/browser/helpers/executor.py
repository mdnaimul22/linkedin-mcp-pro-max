"""
Universal Field Discovery Engine
Analyze any page to discover all interactive input fields,
providing a structured map of all form elements: inputs, textareas, selects, buttons.

Example URLs:
    https://www.google.com/
    https://jsontotable.org/test-api
"""

import asyncio
import logging
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag
from patchright.async_api import Page
from schema import FieldInfo, DiscoveryResult

logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Tags we care about — extensible without touching core logic
_DISCOVERABLE_TAGS: list[str] = ["input", "textarea", "select", "button"]

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
        label=_resolve_label(tag, soup),
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ApiExecutor:
    def __init__(self, page: Page, **kwargs: Any) -> None:
        self._page = page
        self._registry_path: Optional[str] = kwargs.get("registry_path")

    async def execute(self, url: str) -> DiscoveryResult:
        """Navigate to a URL and return a structured map of all discovered input fields.

        Args:
            url: The target URL to analyze.

        Returns:
            DiscoveryResult with categorized fields and a summary.
        """
        logger.info("Field Discovery Engine: navigating to %s", url)

        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(_PAGE_LOAD_SETTLE_SECONDS)

            html = await self._page.content()
            soup = BeautifulSoup(html, "lxml")

            result = DiscoveryResult(url=url)

            for tag in soup.find_all(_DISCOVERABLE_TAGS):
                field = _extract_field(tag, soup)

                match tag.name:
                    case "input":
                        result.inputs.append(field)
                    case "textarea":
                        result.textareas.append(field)
                    case "select":
                        result.selects.append(field)
                    case "button":
                        result.buttons.append(field)

            result.rebuild_summary()

            logger.info(
                "Discovery complete for %s — %d inputs, %d textareas, %d selects, %d buttons",
                url,
                result.summary.total_inputs,
                result.summary.total_textareas,
                result.summary.total_selects,
                result.summary.total_buttons,
            )
            return result

        except Exception as exc:
            logger.error("Field discovery failed at %s: %s", url, exc)
            return DiscoveryResult(url=url, success=False, error=str(exc))