"""Profile and company service with API and browser orchestration.

Dependency Rule:
  imports FROM: schema, api, browser, helpers, services/helpers
  MUST NOT import: providers, tools
"""

import logging
from typing import Optional

from schema.profile import Profile, CompanyInfo
from api.linkedin import LinkedInClient
from browser.manager import BrowserManager
from config.settings import get_settings
from helpers.exceptions import LinkedInMCPError
from services.helpers.mapping import map_profile_browser

logger = logging.getLogger("linkedin-mcp.services.profile")


class ProfileService:
    """Standardized service for LinkedIn profile and company data."""

    def __init__(
        self,
        client: LinkedInClient,
        browser: Optional[BrowserManager] = None,
    ) -> None:
        self._client = client
        self._browser = browser

    async def resolve_profile_id(self, profile_id: str) -> str:
        """Resolve 'me' to the authenticated user's profile ID.

        Strategy: Browser (current session truth) -> Settings fallback.

        Args:
            profile_id: Raw profile identifier or 'me'.

        Returns:
            Resolved LinkedIn username/slug.

        Raises:
            LinkedInMCPError: If 'me' cannot be resolved.
        """
        if profile_id != "me":
            return profile_id

        # 1. Try browser first (source of truth for the current session)
        if self._browser:
            try:
                resolved_id = await self._browser.get_current_profile_id()
                if resolved_id:
                    return resolved_id
            except Exception:
                logger.debug("Failed to resolve profile ID via browser")

        # 2. Fallback to settings
        username = get_settings().linkedin_username
        if not username:
            raise LinkedInMCPError(
                "LinkedIn username not configured. Set LINKEDIN_USERNAME environment variable."
            )
        return username

    async def get_profile(
        self, profile_id: str, use_browser_fallback: bool = True
    ) -> Profile:
        """
        Get profile data using a two-tier strategy:
        1. API Fetch (primary source)
        2. Browser Scraping (fallback if API is 'thin' or blocked)
        """
        target_id = await self.resolve_profile_id(profile_id)
        profile: Profile | None = None

        # 1. API Fetch
        try:
            profile = await self._client.get_profile(target_id)
        except Exception as exc:
            logger.warning("API fetch failed for %s: %s", target_id, exc)

        # 2. Browser Enrichment (if API failed or returned thin data)
        is_thin = not profile or not profile.skills or not profile.experience
        if is_thin and use_browser_fallback and self._browser:
            logger.info("Attempting high-fidelity browser scraping for %s", target_id)
            try:
                raw_data = await self._browser.scrape_profile_by_id(target_id)
                browser_profile = map_profile_browser(target_id, raw_data)

                if profile:
                    # Merge: Browser data takes precedence for details
                    profile.skills = browser_profile.skills or profile.skills
                    profile.experience = (
                        browser_profile.experience or profile.experience
                    )
                    profile.education = browser_profile.education or profile.education
                    profile.summary = browser_profile.summary or profile.summary
                else:
                    profile = browser_profile
            except Exception as exc:
                logger.error("Browser enrichment failed: %s", exc)

        if not profile:
            raise ValueError(f"Could not retrieve profile {target_id} from any source.")

        # Deduplicate experiences
        seen_exp: set[tuple[str, ...]] = set()
        unique_exp = []
        for e in profile.experience:
            identifier = (e.title, e.company, e.start_date, e.end_date)
            if identifier not in seen_exp:
                seen_exp.add(identifier)
                unique_exp.append(e)
        profile.experience = unique_exp

        # Deduplicate skills
        seen_skills: set[str] = set()
        unique_skills = []
        for s in profile.skills:
            if s not in seen_skills:
                seen_skills.add(s)
                unique_skills.append(s)
        profile.skills = unique_skills

        return profile

    async def get_company(self, company_id: str) -> CompanyInfo:
        """Get company info from the LinkedIn API."""
        return await self._client.get_company(company_id)


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="profiles",
    cls=ProfileService,
    deps=['client', 'browser'],
    lazy=True,
)
