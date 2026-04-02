"""LinkedIn Account specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import LinkedInAccount
from db.categories.base import BaseRepository


class LinkedInAccountRepository(BaseRepository[LinkedInAccount]):
    """Repository for LinkedIn account management."""

    def __init__(self) -> None:
        super().__init__(LinkedInAccount)

    async def get_by_member_id(
        self, db: AsyncSession, member_id: str
    ) -> Optional[LinkedInAccount]:
        """Fetch an account by LinkedIn Member ID."""
        result = await db.execute(
            select(LinkedInAccount).filter(
                LinkedInAccount.linkedin_member_id == member_id
            )
        )
        return result.scalars().first()

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[LinkedInAccount]:
        """Fetch all LinkedIn accounts for a specific tenant."""
        result = await db.execute(
            select(LinkedInAccount).filter(LinkedInAccount.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def list_by_user(
        self, db: AsyncSession, user_id: UUID
    ) -> List[LinkedInAccount]:
        """Fetch LinkedIn accounts owned by a specific user."""
        result = await db.execute(
            select(LinkedInAccount).filter(LinkedInAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def list_healthy(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[LinkedInAccount]:
        """Fetch active/healthy LinkedIn accounts for a tenant."""
        result = await db.execute(
            select(LinkedInAccount).filter(
                LinkedInAccount.tenant_id == tenant_id,
                LinkedInAccount.account_status == "active",
            )
        )
        return list(result.scalars().all())
