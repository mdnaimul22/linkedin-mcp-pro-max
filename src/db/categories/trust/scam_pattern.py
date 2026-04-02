"""Scam Pattern specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import ScamPattern
from db.categories.base import BaseRepository


class ScamPatternRepository(BaseRepository[ScamPattern]):
    """Repository for managing scam detection patterns."""

    def __init__(self) -> None:
        super().__init__(ScamPattern)

    async def get_by_name(
        self, db: AsyncSession, pattern_name: str
    ) -> ScamPattern | None:
        """Fetch a specific pattern by its name."""
        result = await db.execute(
            select(ScamPattern).filter(ScamPattern.pattern_name == pattern_name)
        )
        return result.scalars().first()

    async def list_active(self, db: AsyncSession) -> list[ScamPattern]:
        """Fetch all active scam patterns, ordered by impact/hit_count."""
        result = await db.execute(
            select(ScamPattern)
            .filter(ScamPattern.is_active.is_(True))
            .order_by(desc(ScamPattern.hit_count))
        )
        return list(result.scalars().all())
