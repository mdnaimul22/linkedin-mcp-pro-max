"""MCP Tool Call specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import MCPToolCall
from db.categories.base import BaseRepository


class MCPToolCallRepository(BaseRepository[MCPToolCall]):
    """Repository for tracking tool executions in sessions."""

    def __init__(self) -> None:
        super().__init__(MCPToolCall)

    async def list_by_session(
        self, db: AsyncSession, session_id: UUID
    ) -> List[MCPToolCall]:
        """Fetch all tool calls for a specific session."""
        result = await db.execute(
            select(MCPToolCall)
            .filter(MCPToolCall.session_id == session_id)
            .order_by(desc(MCPToolCall.created_at))
        )
        return list(result.scalars().all())

    async def list_recent_by_tenant(
        self, db: AsyncSession, tenant_id: UUID, limit: int = 100
    ) -> List[MCPToolCall]:
        """Fetch the most recent tool calls for a specific tenant."""
        result = await db.execute(
            select(MCPToolCall)
            .filter(MCPToolCall.tenant_id == tenant_id)
            .order_by(desc(MCPToolCall.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_account(
        self, db: AsyncSession, account_id: UUID, limit: int = 50
    ) -> List[MCPToolCall]:
        """Fetch tool calls performed using a specific LinkedIn account."""
        result = await db.execute(
            select(MCPToolCall)
            .filter(MCPToolCall.linkedin_account_id == account_id)
            .order_by(desc(MCPToolCall.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
