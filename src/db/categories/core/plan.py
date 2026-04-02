"""Plan-specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Plan
from db.categories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    """Repository for subscription plan management."""

    def __init__(self) -> None:
        super().__init__(Plan)

    async def get_by_name(self, db: AsyncSession, name: str) -> Plan | None:
        """Fetch a single plan by its unique name."""
        result = await db.execute(select(Plan).filter(Plan.name == name))
        return result.scalars().first()

    async def list_active(self, db: AsyncSession) -> list[Plan]:
        """Fetch all active plans."""
        result = await db.execute(select(Plan).filter(Plan.is_active.is_(True)))
        return list(result.scalars().all())
