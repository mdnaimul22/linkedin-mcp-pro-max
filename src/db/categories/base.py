"""Base repository with generic operations.

Dependency Rule:
    imports FROM: db.tables, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Generic type for SQLAlchemy models
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository for basic CRUD operations."""

    def __init__(self, model: type[T]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, entity_id: UUID) -> T | None:
        """Fetch a single record by its UUID."""
        result = await db.execute(select(self.model).filter(self.model.id == entity_id))
        return result.scalars().first()

    async def first(self, db: AsyncSession, **filters: object) -> T | None:
        """Fetch the first record matching the given filters."""
        stmt = select(self.model).filter_by(**filters)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list(
        self, db: AsyncSession, limit: int = 100, offset: int = 0, **filters: object
    ) -> list[T]:
        """Fetch a list of records with pagination and optional filtering."""
        stmt = select(self.model).filter_by(**filters).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, **kwargs: object) -> T:
        """Create and add a new record to the database."""
        obj = self.model(**kwargs)
        db.add(obj)
        await db.flush()
        return obj

    async def update(
        self, db: AsyncSession, entity_id: UUID, **updates: object
    ) -> T | None:
        """Update a record by its UUID."""
        obj = await self.get(db, entity_id)
        if not obj:
            return None
        for key, value in updates.items():
            setattr(obj, key, value)
        await db.flush()
        return obj

    async def delete(self, db: AsyncSession, entity_id: UUID) -> bool:
        """Delete a record by its UUID."""
        obj = await self.get(db, entity_id)
        if not obj:
            return False
        await db.delete(obj)
        await db.flush()
        return True
