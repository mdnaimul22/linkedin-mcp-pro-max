"""Profile Experience specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import ProfileExperience
from db.categories.base import BaseRepository


class ProfileExperienceRepository(BaseRepository[ProfileExperience]):
    """Repository for profile work experience management."""

    def __init__(self) -> None:
        super().__init__(ProfileExperience)

    async def list_by_profile(
        self, db: AsyncSession, profile_id: UUID
    ) -> List[ProfileExperience]:
        """Fetch all work experiences for a specific profile."""
        result = await db.execute(
            select(ProfileExperience)
            .filter(ProfileExperience.profile_id == profile_id)
            .order_by(desc(ProfileExperience.started_at))
        )
        return list(result.scalars().all())
