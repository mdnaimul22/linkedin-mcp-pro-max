"""Profile Education specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import ProfileEducation
from db.categories.base import BaseRepository


class ProfileEducationRepository(BaseRepository[ProfileEducation]):
    """Repository for profile education history management."""

    def __init__(self) -> None:
        super().__init__(ProfileEducation)

    async def list_by_profile(
        self, db: AsyncSession, profile_id: UUID
    ) -> List[ProfileEducation]:
        """Fetch all education records for a specific profile."""
        result = await db.execute(
            select(ProfileEducation)
            .filter(ProfileEducation.profile_id == profile_id)
            .order_by(desc(ProfileEducation.started_at))
        )
        return list(result.scalars().all())
