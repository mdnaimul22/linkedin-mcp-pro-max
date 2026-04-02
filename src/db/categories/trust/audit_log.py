"""Audit Log specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import AuditLog
from db.categories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for system auditing and compliance logs."""

    def __init__(self) -> None:
        super().__init__(AuditLog)

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID, limit: int = 100
    ) -> List[AuditLog]:
        """Fetch all audit logs for a specific tenant."""
        result = await db.execute(
            select(AuditLog)
            .filter(AuditLog.tenant_id == tenant_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_user(self, db: AsyncSession, user_id: UUID) -> List[AuditLog]:
        """Fetch all audit logs performed by a specific user."""
        result = await db.execute(
            select(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
        )
        return list(result.scalars().all())

    async def list_by_resource(
        self, db: AsyncSession, resource_type: str, resource_id: UUID
    ) -> List[AuditLog]:
        """Fetch all audit logs for a specific resource."""
        result = await db.execute(
            select(AuditLog)
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(desc(AuditLog.created_at))
        )
        return list(result.scalars().all())
