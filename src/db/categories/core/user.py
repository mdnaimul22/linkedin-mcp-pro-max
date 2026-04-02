"""User-specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import User
from db.categories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for user management."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a single user by their email address."""
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def list_by_tenant(self, db: AsyncSession, tenant_id: UUID) -> list[User]:
        """Fetch all users belonging to a specific tenant."""
        result = await db.execute(select(User).filter(User.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def list_by_role(self, db: AsyncSession, role: str) -> list[User]:
        """Fetch all users with a specific role."""
        result = await db.execute(select(User).filter(User.role == role))
        return list(result.scalars().all())
