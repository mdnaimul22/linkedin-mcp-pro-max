"""Subscription specific repository operations.

Dependency Rule:
    imports FROM: db.tables, db.repositories/base, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.tables import Subscription
from db.categories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for managing tenant subscriptions and billing status."""

    def __init__(self) -> None:
        super().__init__(Subscription)

    async def get_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> Optional[Subscription]:
        """Fetch the current subscription for a tenant."""
        result = await db.execute(
            select(Subscription).filter(Subscription.tenant_id == tenant_id)
        )
        return result.scalars().first()

    async def get_by_stripe_id(
        self, db: AsyncSession, stripe_id: str
    ) -> Optional[Subscription]:
        """Fetch a subscription by its Stripe ID."""
        result = await db.execute(
            select(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_id
            )
        )
        return result.scalars().first()

    async def get_active_by_tenant(
        self, db: AsyncSession, tenant_id: UUID
    ) -> Optional[Subscription]:
        """Fetch the active/trialing subscription for a tenant."""
        result = await db.execute(
            select(Subscription).filter(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(["active", "trialing"]),
            )
        )
        return result.scalars().first()
