"""Company Job Posting specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import CompanyJobPosting
from db.categories.base import BaseRepository


class CompanyJobPostingRepository(BaseRepository[CompanyJobPosting]):
    """Repository for managing company job openings."""

    def __init__(self) -> None:
        super().__init__(CompanyJobPosting)

    async def list_by_company(
        self, db: AsyncSession, company_id: UUID
    ) -> list[CompanyJobPosting]:
        """Fetch all job postings for a company."""
        result = await db.execute(
            select(CompanyJobPosting)
            .filter(CompanyJobPosting.company_id == company_id)
            .order_by(desc(CompanyJobPosting.posted_at))
        )
        return list(result.scalars().all())

    async def list_active(
        self, db: AsyncSession, company_id: UUID
    ) -> list[CompanyJobPosting]:
        """Fetch active job postings for a company."""
        result = await db.execute(
            select(CompanyJobPosting)
            .filter(
                CompanyJobPosting.company_id == company_id,
                CompanyJobPosting.is_active.is_(True),
            )
            .order_by(desc(CompanyJobPosting.posted_at))
        )
        return list(result.scalars().all())
