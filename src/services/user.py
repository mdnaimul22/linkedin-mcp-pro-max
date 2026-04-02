"""User management business logic.

Dependency Rule:
    imports FROM: db, schema, exceptions
    MUST NOT import: browser, session, tools, app
"""

import logging
from typing import Optional, List
from uuid import UUID

from passlib.context import CryptContext

from db.database import DatabaseService
from schema.core import User as UserSchema, UserCreate, UserUpdate

logger = logging.getLogger("linkedin-mcp.services.user")

# Setup password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for managing core application users."""

    def __init__(self, db: DatabaseService) -> None:
        self.db = db

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    async def get_user(self, user_id: UUID) -> Optional[UserSchema]:
        async with self.db.get_session() as session:
            user = await self.db.users.get(session, user_id)
            return UserSchema.model_validate(user) if user else None

    async def get_user_by_email(self, email: str) -> Optional[UserSchema]:
        async with self.db.get_session() as session:
            user = await self.db.users.first(session, email=email)
            return UserSchema.model_validate(user) if user else None

    async def create_user(self, data: UserCreate) -> UserSchema:
        existing = await self.get_user_by_email(data.email)
        if existing:
            raise ValueError(f"User {data.email} exists")

        async with self.db.get_session() as session:
            user = await self.db.users.create(session, **data.model_dump())
            return UserSchema.model_validate(user)

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[UserSchema]:
        async with self.db.get_session() as session:
            user = await self.db.users.first(session, email=email)
            if (
                not user
                or not user.password_hash
                or not self._verify_password(password, user.password_hash)
            ):
                return None
            return UserSchema.model_validate(user)

    async def list_users(self, tenant_id: Optional[UUID] = None) -> List[UserSchema]:
        async with self.db.get_session() as session:
            if tenant_id:
                users = await self.db.users.list(session, tenant_id=tenant_id)
            else:
                users = await self.db.users.list(session)
            return [UserSchema.model_validate(u) for u in users]

    async def update_user(self, user_id: UUID, updates: UserUpdate) -> UserSchema:
        async with self.db.get_session() as session:
            user = await self.db.users.update(
                session, user_id, **updates.model_dump(exclude_unset=True)
            )
            return UserSchema.model_validate(user)


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="users",
    cls=UserService,
    deps=['db'],
    lazy=False,
)
