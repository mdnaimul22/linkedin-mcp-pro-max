"""Tenant-specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Tenant
from db.categories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for tenant management."""

    def __init__(self) -> None:
        super().__init__(Tenant)

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Tenant]:
        """Fetch a single tenant by their slug."""
        result = await db.execute(select(Tenant).filter(Tenant.slug == slug))
        return result.scalars().first()

    async def list_by_status(self, db: AsyncSession, status: str) -> list[Tenant]:
        """Fetch all tenants with a specific status."""
        result = await db.execute(select(Tenant).filter(Tenant.status == status))
        return list(result.scalars().all())
