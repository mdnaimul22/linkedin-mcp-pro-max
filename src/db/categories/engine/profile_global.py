"""LinkedIn Profile Global specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import LinkedInProfileGlobal
from db.categories.base import BaseRepository


class LinkedInProfileGlobalRepository(BaseRepository[LinkedInProfileGlobal]):
    """Repository for global LinkedIn profile intelligence."""

    def __init__(self) -> None:
        super().__init__(LinkedInProfileGlobal)

    async def get_by_linkedin_id(
        self, db: AsyncSession, linkedin_id: str
    ) -> Optional[LinkedInProfileGlobal]:
        """Fetch a profile by LinkedIn ID."""
        result = await db.execute(
            select(LinkedInProfileGlobal).filter(
                LinkedInProfileGlobal.linkedin_id == linkedin_id
            )
        )
        return result.scalars().first()

    async def get_by_url(
        self, db: AsyncSession, profile_url: str
    ) -> Optional[LinkedInProfileGlobal]:
        """Fetch a profile by LinkedIn Profile URL."""
        result = await db.execute(
            select(LinkedInProfileGlobal).filter(
                LinkedInProfileGlobal.profile_url == profile_url
            )
        )
        return result.scalars().first()

    async def search_by_name(
        self, db: AsyncSession, query: str, limit: int = 10
    ) -> List[LinkedInProfileGlobal]:
        """Fetch profiles matching a name string."""
        result = await db.execute(
            select(LinkedInProfileGlobal)
            .filter(LinkedInProfileGlobal.full_name.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars().all())
