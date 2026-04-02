"""MCP Session specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import MCPSession
from db.categories.base import BaseRepository


class MCPSessionRepository(BaseRepository[MCPSession]):
    """Repository for MCP session tracking and lifecycle."""

    def __init__(self) -> None:
        super().__init__(MCPSession)

    async def list_active_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[MCPSession]:
        """Fetch all active/open sessions for a tenant."""
        result = await db.execute(
            select(MCPSession)
            .filter(
                MCPSession.tenant_id == tenant_id,
                MCPSession.status.in_(["active", "idle"]),
            )
            .order_by(desc(MCPSession.started_at))
        )
        return list(result.scalars().all())

    async def list_by_user(
        self, db: AsyncSession, user_id: UUID, limit: int = 50
    ) -> List[MCPSession]:
        """Fetch all sessions for a specific user."""
        result = await db.execute(
            select(MCPSession)
            .filter(MCPSession.user_id == user_id)
            .order_by(desc(MCPSession.started_at))
            .limit(limit)
        )
        return list(result.scalars().all())
