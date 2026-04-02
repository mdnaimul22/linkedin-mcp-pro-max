"""Message Template specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import MessageTemplate
from db.categories.base import BaseRepository


class MessageTemplateRepository(BaseRepository[MessageTemplate]):
    """Repository for managing communication message templates."""

    def __init__(self) -> None:
        super().__init__(MessageTemplate)

    async def list_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> List[MessageTemplate]:
        """Fetch all message templates for a specific tenant."""
        result = await db.execute(
            select(MessageTemplate).filter(MessageTemplate.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def list_by_type(
        self, db: AsyncSession, tenant_id: UUID, template_type: str
    ) -> List[MessageTemplate]:
        """Fetch templates for a tenant filtered by type."""
        result = await db.execute(
            select(MessageTemplate).filter(
                MessageTemplate.tenant_id == tenant_id,
                MessageTemplate.template_type == template_type,
            )
        )
        return list(result.scalars().all())
