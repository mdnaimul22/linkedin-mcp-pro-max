"""Data Request specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import DataRequest
from db.categories.base import BaseRepository


class DataRequestRepository(BaseRepository[DataRequest]):
    """Repository for managing user data privacy requests (GDPR)."""

    def __init__(self) -> None:
        super().__init__(DataRequest)

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[DataRequest]:
        """Fetch all data requests for a specific tenant."""
        result = await db.execute(
            select(DataRequest)
            .filter(DataRequest.tenant_id == tenant_id)
            .order_by(desc(DataRequest.created_at))
        )
        return list(result.scalars().all())

    async def list_by_status(self, db: AsyncSession, status: str) -> List[DataRequest]:
        """Fetch data requests filtered by their current status."""
        result = await db.execute(
            select(DataRequest)
            .filter(DataRequest.status == status)
            .order_by(desc(DataRequest.created_at))
        )
        return list(result.scalars().all())
