"""Campaign Step Execution specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import CampaignStepExecution
from db.categories.base import BaseRepository


class CampaignStepExecutionRepository(BaseRepository[CampaignStepExecution]):
    """Repository for tracking the results of campaign step executions."""

    def __init__(self) -> None:
        super().__init__(CampaignStepExecution)

    async def list_by_enrollment(
        self, db: AsyncSession, enrollment_id: UUID
    ) -> List[CampaignStepExecution]:
        """Fetch all step executions for a specific enrollment."""
        result = await db.execute(
            select(CampaignStepExecution)
            .filter(CampaignStepExecution.enrollment_id == enrollment_id)
            .order_by(desc(CampaignStepExecution.executed_at))
        )
        return list(result.scalars().all())

    async def get_latest_for_enrollment(
        self, db: AsyncSession, enrollment_id: UUID
    ) -> Optional[CampaignStepExecution]:
        """Fetch the most recent step execution for an enrollment."""
        result = await db.execute(
            select(CampaignStepExecution)
            .filter(CampaignStepExecution.enrollment_id == enrollment_id)
            .order_by(desc(CampaignStepExecution.executed_at))
            .limit(1)
        )
        return result.scalars().first()
