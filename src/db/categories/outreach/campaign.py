"""Campaign specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Campaign
from db.categories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for managing outreach campaigns and execution status."""

    def __init__(self) -> None:
        super().__init__(Campaign)

    async def list_by_tenant(self, db: AsyncSession, tenant_id: UUID) -> List[Campaign]:
        """Fetch all campaigns for a specific tenant."""
        result = await db.execute(
            select(Campaign)
            .filter(Campaign.tenant_id == tenant_id)
            .order_by(desc(Campaign.created_at))
        )
        return list(result.scalars().all())

    async def list_by_status(
        self, db: AsyncSession, tenant_id: UUID, status: str
    ) -> List[Campaign]:
        """Fetch campaigns for a tenant filtered by status."""
        result = await db.execute(
            select(Campaign)
            .filter(Campaign.tenant_id == tenant_id, Campaign.status == status)
            .order_by(desc(Campaign.created_at))
        )
        return list(result.scalars().all())
