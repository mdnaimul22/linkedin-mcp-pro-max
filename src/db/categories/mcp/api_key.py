"""API Key specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import APIKey
from db.categories.base import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for API key management and authentication."""

    def __init__(self) -> None:
        super().__init__(APIKey)

    async def get_by_hash(self, db: AsyncSession, key_hash: str) -> Optional[APIKey]:
        """Fetch an API key by its hash."""
        result = await db.execute(select(APIKey).filter(APIKey.key_hash == key_hash))
        return result.scalars().first()

    async def list_by_tenant(self, db: AsyncSession, tenant_id: UUID) -> List[APIKey]:
        """Fetch all API keys for a specific tenant."""
        result = await db.execute(select(APIKey).filter(APIKey.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def list_by_user(self, db: AsyncSession, user_id: UUID) -> List[APIKey]:
        """Fetch all API keys for a specific user."""
        result = await db.execute(select(APIKey).filter(APIKey.user_id == user_id))
        return list(result.scalars().all())
