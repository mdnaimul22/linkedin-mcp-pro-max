"""Tenant management business logic.

Dependency Rule:
    imports FROM: db, schema, exceptions
    MUST NOT import: browser, session, tools, app
"""

import logging
from typing import Optional, List
from uuid import UUID

from db.database import DatabaseService
from schema.core import Tenant as TenantSchema, TenantCreate, TenantUpdate

logger = logging.getLogger("linkedin-mcp.services.tenant")


class TenantService:
    """Service for managing core application tenants."""

    def __init__(self, db: DatabaseService) -> None:
        self.db = db

    async def get_tenant(self, tenant_id: UUID) -> Optional[TenantSchema]:
        async with self.db.get_session() as session:
            tenant = await self.db.tenants.get(session, tenant_id)
            return TenantSchema.model_validate(tenant) if tenant else None

    async def create_tenant(self, data: TenantCreate) -> TenantSchema:
        async with self.db.get_session() as session:
            tenant = await self.db.tenants.create(session, **data.model_dump())
            return TenantSchema.model_validate(tenant)

    async def update_tenant(
        self, tenant_id: UUID, updates: TenantUpdate
    ) -> TenantSchema:
        async with self.db.get_session() as session:
            tenant = await self.db.tenants.update(
                session, tenant_id, **updates.model_dump(exclude_unset=True)
            )
            return TenantSchema.model_validate(tenant)

    async def list_tenants(self) -> List[TenantSchema]:
        async with self.db.get_session() as session:
            tenants = await self.db.tenants.list(session)
            return [TenantSchema.model_validate(t) for t in tenants]

    async def get_or_create_default_tenant(self) -> TenantSchema:
        async with self.db.get_session() as session:
            tenants = await self.db.tenants.list(session)
            if tenants:
                return TenantSchema.model_validate(tenants[0])

            tenant = await self.db.tenants.create(
                session,
                name="Local User",
                slug="local-user",
                billing_email="local@example.com",
                status="active",
            )
            return TenantSchema.model_validate(tenant)


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="tenants",
    cls=TenantService,
    deps=['db'],
    lazy=False,
)
