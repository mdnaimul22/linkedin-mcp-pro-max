"""Usage Record specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import UsageRecord
from db.categories.base import BaseRepository


class UsageRecordRepository(BaseRepository[UsageRecord]):
    """Repository for managing metered usage tracking."""

    def __init__(self) -> None:
        super().__init__(UsageRecord)

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[UsageRecord]:
        """Fetch all usage records for a specific tenant."""
        result = await db.execute(
            select(UsageRecord)
            .filter(UsageRecord.tenant_id == tenant_id)
            .order_by(desc(UsageRecord.recorded_at))
        )
        return list(result.scalars().all())

    async def get_latest_metric(
        self, db: AsyncSession, tenant_id: UUID, metric: str
    ) -> List[UsageRecord]:
        """Fetch the most recent usage records for a specific metric."""
        result = await db.execute(
            select(UsageRecord)
            .filter(UsageRecord.tenant_id == tenant_id, UsageRecord.metric == metric)
            .order_by(desc(UsageRecord.recorded_at))
        )
        return list(result.scalars().all())
