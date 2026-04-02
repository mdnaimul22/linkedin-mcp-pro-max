"""Invoice specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Invoice
from db.categories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for managing billing history and invoices."""

    def __init__(self) -> None:
        super().__init__(Invoice)

    async def list_by_tenant(self, db: AsyncSession, tenant_id: UUID) -> List[Invoice]:
        """Fetch all invoices for a specific tenant."""
        result = await db.execute(
            select(Invoice)
            .filter(Invoice.tenant_id == tenant_id)
            .order_by(desc(Invoice.created_at))
        )
        return list(result.scalars().all())

    async def get_by_stripe_id(
        self, db: AsyncSession, stripe_id: str
    ) -> Optional[Invoice]:
        """Fetch an invoice by its Stripe ID."""
        result = await db.execute(
            select(Invoice).filter(Invoice.stripe_invoice_id == stripe_id)
        )
        return result.scalars().first()
