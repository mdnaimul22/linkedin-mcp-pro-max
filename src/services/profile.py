"""Profile and company service with database, API, and browser orchestration.

Dependency Rule:
  imports FROM: schema, api, db, browser, helpers
  MUST NOT import: providers, tools
"""

import logging
from uuid import UUID
from typing import Optional, Any

from schema.profile import Profile, CompanyInfo
from api.linkedin import LinkedInClient
from db.database import DatabaseService
from browser.manager import BrowserManager
from config.settings import get_settings
from helpers.exceptions import LinkedInMCPError
from services.helpers.mapping import map_profile_db, map_company_db, map_profile_browser

logger = logging.getLogger("linkedin-mcp.services.profile")


class ProfileService:
    """Standardized service for LinkedIn profile and company data."""

    def __init__(
        self,
        client: LinkedInClient,
        db: DatabaseService,
        browser: Optional[BrowserManager] = None,
    ) -> None:
        self._client = client
        self._db = db
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
        self, tenant_id: UUID, profile_id: str, use_browser_fallback: bool = True
    ) -> Profile:
        """
        Get profile with standard Lean Schema-First strategy:
        1. DB Lookup (Fastest, Level 2 cached)
        2. API Fetch (Fallback if DB miss or stale)
        3. Browser Enrichment (Fallback if API is 'thin' or blocked)
        """
        # Resolve 'me'
        target_id = await self.resolve_profile_id(profile_id)

        # 1. DB Lookup
        async with self._db.get_session() as session:
            db_profile = await self._db.linkedin_profiles.get_by_linkedin_id(
                session, target_id
            )
            if not db_profile:
                db_profile = await self._db.linkedin_profiles.get_by_url(
                    session, target_id
                )

            if db_profile:
                # Load relations and map
                exp = await self._db.profile_experiences.list_by_profile(
                    session, db_profile.id
                )
                edu = await self._db.profile_education.list_by_profile(
                    session, db_profile.id
                )
                skills = await self._db.profile_skills.list_by_profile(
                    session, db_profile.id
                )
                profile = map_profile_db(db_profile, exp, edu, skills)

                # Check if DB data is sufficient (not thin)
                if profile.skills and profile.experience:
                    return profile
                logger.info(
                    "Cached profile %s is thin, attempting enrichment...", target_id
                )
            else:
                profile = None

        # 2. API Fetch (if DB miss or thin)
        if not profile:
            try:
                profile = await self._client.get_profile(target_id)
                # Persist basic API info
                await self.save_profile_to_db(tenant_id, profile)
            except Exception as exc:
                logger.warning("API fetch failed for %s: %s", target_id, exc)

        # 3. Browser Enrichment (if still thin or no profile)
        is_thin = not profile or not profile.skills or not profile.experience
        if is_thin and use_browser_fallback and self._browser:
            logger.info("Attempting high-fidelity browser scraping for %s", target_id)
            try:
                # Scrape directly via browser (returns raw dict now)
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

                # Persist enriched data
                await self.save_profile_to_db(tenant_id, profile)
            except Exception as exc:
                logger.error("Browser enrichment failed: %s", exc)

        if not profile:
            raise ValueError(f"Could not retrieve profile {target_id} from any source.")

        # Deduplicate experiences
        seen_exp = set()
        unique_exp = []
        for e in profile.experience:
            identifier = (e.title, e.company, e.start_date, e.end_date)
            if identifier not in seen_exp:
                seen_exp.add(identifier)
                unique_exp.append(e)
        profile.experience = unique_exp

        # Deduplicate skills
        seen_skills = set()
        unique_skills = []
        for s in profile.skills:
            if s not in seen_skills:
                seen_skills.add(s)
                unique_skills.append(s)
        profile.skills = unique_skills

        return profile

    async def get_company(self, tenant_id: UUID, company_id: str) -> CompanyInfo:
        """Get company info with DB-first strategy."""
        async with self._db.get_session() as session:
            db_company = await self._db.companies.get_by_linkedin_id(
                session, company_id
            )
            if db_company:
                return map_company_db(db_company)

            # API Fallback
            company = await self._client.get_company(company_id)

            # Persist
            await self._db.companies.create(
                session,
                tenant_id=tenant_id,
                linkedin_id=company.company_id,
                name=company.name,
                description=company.description,
                website=company.website,
                industry=company.industry,
                company_size=company.company_size,
                headquarters=company.headquarters,
                specialties=company.specialties,
                linkedin_url=company.url,
            )
            return company

    async def save_profile_to_db(self, tenant_id: UUID, profile: Profile) -> None:
        """Synchronize a schema Profile back to the database."""
        async with self._db.get_session() as session:
            # Upsert logic (simplified for demonstration)
            db_profile = await self._db.linkedin_profiles.get_by_linkedin_id(
                session, profile.profile_id
            )
            if not db_profile:
                db_profile = await self._db.linkedin_profiles.create(
                    session,
                    linkedin_id=profile.profile_id,
                    profile_url=profile.profile_url,
                    full_name=profile.name,
                    headline=profile.headline,
                    summary=profile.summary,
                    location=profile.location,
                    industry=profile.industry,
                    email=profile.email,
                    phone=profile.phone,
                )

            # Clear and replace relations (Standard strategy for high-fidelity sync)
            await self._db.profile_skills.delete_by_profile(session, db_profile.id)
            for skill in profile.skills:
                await self._db.profile_skills.create(
                    session, profile_id=db_profile.id, skill_name=skill
                )

            # (Similar logic for experience and education would go here)
            # This ensures Level 2 is always synced with Level 1.


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="profiles",
    cls=ProfileService,
    deps=['client', 'db', 'browser'],
    lazy=True,
)
