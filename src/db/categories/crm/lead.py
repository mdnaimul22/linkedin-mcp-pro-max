"""Lead specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Lead
from db.categories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    """Repository for lead management and tracking."""

    def __init__(self) -> None:
        super().__init__(Lead)

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID, limit: int = 100
    ) -> List[Lead]:
        """Fetch all leads for a specific tenant."""
        result = await db.execute(
            select(Lead)
            .filter(Lead.tenant_id == tenant_id)
            .order_by(desc(Lead.lead_score))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_status(
        self, db: AsyncSession, tenant_id: UUID, status: str
    ) -> List[Lead]:
        """Fetch leads for a tenant filtered by current status."""
        result = await db.execute(
            select(Lead)
            .filter(Lead.tenant_id == tenant_id, Lead.status == status)
            .order_by(desc(Lead.lead_score))
        )
        return list(result.scalars().all())

    async def list_assigned_to(self, db: AsyncSession, user_id: UUID) -> List[Lead]:
        """Fetch leads assigned to a specific user (SDR/BDR)."""
        result = await db.execute(select(Lead).filter(Lead.assigned_to == user_id))
        return list(result.scalars().all())

    async def get_by_profile(
        self, db: AsyncSession, tenant_id: UUID, profile_id: UUID
    ) -> Optional[Lead]:
        """Fetch a specific lead by profile ID within a tenant context."""
        result = await db.execute(
            select(Lead).filter(
                Lead.tenant_id == tenant_id, Lead.profile_id == profile_id
            )
        )
        return result.scalars().first()
