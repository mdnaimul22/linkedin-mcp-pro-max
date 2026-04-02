"""Lead Activity specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import LeadActivity
from db.categories.base import BaseRepository


class LeadActivityRepository(BaseRepository[LeadActivity]):
    """Repository for lead interaction history."""

    def __init__(self) -> None:
        super().__init__(LeadActivity)

    async def list_by_lead(
        self, db: AsyncSession, lead_id: UUID, limit: int = 50
    ) -> List[LeadActivity]:
        """Fetch all activities for a specific lead."""
        result = await db.execute(
            select(LeadActivity)
            .filter(LeadActivity.lead_id == lead_id)
            .order_by(desc(LeadActivity.occurred_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_type(
        self, db: AsyncSession, lead_id: UUID, activity_type: str
    ) -> List[LeadActivity]:
        """Fetch activities for a lead filtered by type."""
        result = await db.execute(
            select(LeadActivity)
            .filter(
                LeadActivity.lead_id == lead_id,
                LeadActivity.activity_type == activity_type,
            )
            .order_by(desc(LeadActivity.occurred_at))
        )
        return list(result.scalars().all())
