"""Scam Report specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import ScamReport
from db.categories.base import BaseRepository


class ScamReportRepository(BaseRepository[ScamReport]):
    """Repository for managing platform safety and scam reports."""

    def __init__(self) -> None:
        super().__init__(ScamReport)

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[ScamReport]:
        """Fetch all scam reports for a specific tenant."""
        result = await db.execute(
            select(ScamReport)
            .filter(ScamReport.tenant_id == tenant_id)
            .order_by(desc(ScamReport.created_at))
        )
        return list(result.scalars().all())

    async def list_by_status(self, db: AsyncSession, status: str) -> List[ScamReport]:
        """Fetch scam reports filtered by their review status."""
        result = await db.execute(
            select(ScamReport)
            .filter(ScamReport.status == status)
            .order_by(desc(ScamReport.created_at))
        )
        return list(result.scalars().all())
