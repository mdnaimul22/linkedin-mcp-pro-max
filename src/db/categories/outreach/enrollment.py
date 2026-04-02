"""Campaign Enrollment specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import CampaignEnrollment
from db.categories.base import BaseRepository


class CampaignEnrollmentRepository(BaseRepository[CampaignEnrollment]):
    """Repository for managing lead enrollments in campaigns."""

    def __init__(self) -> None:
        super().__init__(CampaignEnrollment)

    async def list_by_campaign(
        self, db: AsyncSession, campaign_id: UUID
    ) -> List[CampaignEnrollment]:
        """Fetch all enrollments for a specific campaign."""
        result = await db.execute(
            select(CampaignEnrollment).filter(
                CampaignEnrollment.campaign_id == campaign_id
            )
        )
        return list(result.scalars().all())

    async def list_by_status(
        self, db: AsyncSession, campaign_id: UUID, status: str
    ) -> List[CampaignEnrollment]:
        """Fetch enrollments for a campaign filtered by status."""
        result = await db.execute(
            select(CampaignEnrollment).filter(
                CampaignEnrollment.campaign_id == campaign_id,
                CampaignEnrollment.status == status,
            )
        )
        return list(result.scalars().all())

    async def get_by_lead(
        self, db: AsyncSession, campaign_id: UUID, lead_id: UUID
    ) -> Optional[CampaignEnrollment]:
        """Fetch enrollment for a specific lead in a campaign."""
        result = await db.execute(
            select(CampaignEnrollment).filter(
                CampaignEnrollment.campaign_id == campaign_id,
                CampaignEnrollment.lead_id == lead_id,
            )
        )
        return result.scalars().first()
