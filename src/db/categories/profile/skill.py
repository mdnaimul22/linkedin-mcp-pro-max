"""Profile Skill specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import ProfileSkill
from db.categories.base import BaseRepository


class ProfileSkillRepository(BaseRepository[ProfileSkill]):
    """Repository for profile skill management."""

    def __init__(self) -> None:
        super().__init__(ProfileSkill)

    async def list_by_profile(
        self, db: AsyncSession, profile_id: UUID
    ) -> List[ProfileSkill]:
        """Fetch all skills for a specific profile."""
        result = await db.execute(
            select(ProfileSkill)
            .filter(ProfileSkill.profile_id == profile_id)
            .order_by(desc(ProfileSkill.endorsement_count))
        )
        return list(result.scalars().all())

    async def delete_by_profile(self, db: AsyncSession, profile_id: UUID) -> int:
        """Delete all skills for a specific profile."""
        from sqlalchemy import delete

        result = await db.execute(
            delete(ProfileSkill).filter(ProfileSkill.profile_id == profile_id)
        )
        return result.rowcount
