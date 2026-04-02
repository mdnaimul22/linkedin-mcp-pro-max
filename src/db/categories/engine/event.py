"""LinkedIn Account Event specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import LinkedInAccountEvent
from db.categories.base import BaseRepository


class LinkedInAccountEventRepository(BaseRepository[LinkedInAccountEvent]):
    """Repository for LinkedIn account event monitoring."""

    def __init__(self) -> None:
        super().__init__(LinkedInAccountEvent)

    async def list_by_account(
        self, db: AsyncSession, account_id: UUID, limit: int = 50
    ) -> List[LinkedInAccountEvent]:
        """Fetch all events for a specific LinkedIn account."""
        result = await db.execute(
            select(LinkedInAccountEvent)
            .filter(LinkedInAccountEvent.account_id == account_id)
            .order_by(desc(LinkedInAccountEvent.occurred_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_type(
        self, db: AsyncSession, account_id: UUID, event_type: str
    ) -> List[LinkedInAccountEvent]:
        """Fetch events for a specific account filtered by type."""
        result = await db.execute(
            select(LinkedInAccountEvent)
            .filter(
                LinkedInAccountEvent.account_id == account_id,
                LinkedInAccountEvent.event_type == event_type,
            )
            .order_by(desc(LinkedInAccountEvent.occurred_at))
        )
        return list(result.scalars().all())
