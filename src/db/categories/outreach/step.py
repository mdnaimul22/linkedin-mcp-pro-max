"""Campaign Step specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import CampaignStep
from db.categories.base import BaseRepository


class CampaignStepRepository(BaseRepository[CampaignStep]):
    """Repository for managing individual campaign sequence steps."""

    def __init__(self) -> None:
        super().__init__(CampaignStep)

    async def list_by_campaign(
        self, db: AsyncSession, campaign_id: UUID
    ) -> List[CampaignStep]:
        """Fetch all steps for a specific campaign, ordered by sequence."""
        result = await db.execute(
            select(CampaignStep)
            .filter(CampaignStep.campaign_id == campaign_id)
            .order_by(CampaignStep.step_order)
        )
        return list(result.scalars().all())
