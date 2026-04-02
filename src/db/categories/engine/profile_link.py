"""Tenant-Profile Link specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import TenantProfileLink
from db.categories.base import BaseRepository


class TenantProfileLinkRepository(BaseRepository[TenantProfileLink]):
    """Repository for links between tenants and global profiles."""

    def __init__(self) -> None:
        super().__init__(TenantProfileLink)

    async def get_link(
        self, db: AsyncSession, tenant_id: UUID, profile_id: UUID
    ) -> Optional[TenantProfileLink]:
        """Fetch a specific link between a tenant and a profile."""
        result = await db.execute(
            select(TenantProfileLink).filter(
                TenantProfileLink.tenant_id == tenant_id,
                TenantProfileLink.profile_id == profile_id,
            )
        )
        return result.scalars().first()

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[TenantProfileLink]:
        """Fetch all profiles linked to a tenant."""
        result = await db.execute(
            select(TenantProfileLink).filter(TenantProfileLink.tenant_id == tenant_id)
        )
        return list(result.scalars().all())
