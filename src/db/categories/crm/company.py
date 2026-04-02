"""Company specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Company
from db.categories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Repository for company data and CRM management."""

    def __init__(self) -> None:
        super().__init__(Company)

    async def get_by_linkedin_id(
        self, db: AsyncSession, linkedin_id: str
    ) -> Optional[Company]:
        """Fetch a company by LinkedIn ID."""
        result = await db.execute(
            select(Company).filter(Company.linkedin_id == linkedin_id)
        )
        return result.scalars().first()

    async def list_by_tenant(self, db: AsyncSession, tenant_id: UUID) -> List[Company]:
        """Fetch all companies linked to a specific tenant."""
        result = await db.execute(
            select(Company).filter(Company.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def list_by_industry(
        self, db: AsyncSession, tenant_id: UUID, industry: str
    ) -> List[Company]:
        """Fetch companies for a tenant filtered by industry."""
        result = await db.execute(
            select(Company).filter(
                Company.tenant_id == tenant_id, Company.industry == industry
            )
        )
        return list(result.scalars().all())
