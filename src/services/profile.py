from typing import Optional

from schema import Profile, CompanyInfo
from providers.linkedin import LinkedInClient
from browser.manager import Manager
from config import Settings, setup_logger
from helpers.exceptions import LinkedInMCPError
from services.helpers.mapping import map_profile_browser

logger = setup_logger(Settings.LOG_DIR / "profile_service.log", name="linkedin-mcp.services.profile")


class ProfileService:
    """Standardized service for LinkedIn profile and company data."""

    def __init__(
        self,
        client: LinkedInClient,
        browser: Optional[Manager] = None,
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
            except Exception as exc:
                logger.debug(f"Failed to resolve profile ID via browser: {exc}")

        # 2. Fallback to settings
        resolved_id = Settings.linkedin_username or Settings.linkedin_email
        
        if not resolved_id:
            raise LinkedInMCPError(
                "LinkedIn username or email not configured. Set LINKEDIN_USERNAME or LINKEDIN_EMAIL."
            )
        return resolved_id

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

        logger.info(f"Fetching profile: {target_id}")

        # 1. API Fetch
        try:
            profile = await self._client.get_profile(target_id)
        except Exception as exc:
            logger.warning(f"API fetch failed for {target_id}: {exc}")

        # 2. Browser Enrichment (if API failed or returned thin data)
        is_thin = not profile or not profile.skills or not profile.experience
        if is_thin and use_browser_fallback and self._browser:
            logger.info(f"Attempting high-fidelity browser scraping for {target_id}")
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

                    # Deduplicate only when a merge happened
                    profile.experience = list(
                        {(e.title, e.company, e.start_date, e.end_date): e for e in profile.experience}.values()
                    )
                    profile.skills = list(dict.fromkeys(profile.skills))
                else:
                    profile = browser_profile
            except Exception as exc:
                logger.error(f"Browser enrichment failed for {target_id}: {exc}")

        if not profile:
            logger.error(f"Failed to retrieve profile {target_id} from all sources.")
            raise ValueError(f"Could not retrieve profile {target_id} from any source.")

        return profile

    async def get_company(self, company_id: str) -> CompanyInfo:
        """Get company info from the LinkedIn API."""
        logger.info(f"Fetching company info: {company_id}")
        return await self._client.get_company(company_id)


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="profiles",
    cls=ProfileService,
    deps=['client', 'browser'],
    lazy=True,
)
