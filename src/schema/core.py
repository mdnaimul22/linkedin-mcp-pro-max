"""Core infrastructure models for Tenants and Users."""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from schema.common import SCHEMA_MODEL_CONFIG


class TenantBase(BaseModel):
    """Base fields for a Tenant."""

    model_config = SCHEMA_MODEL_CONFIG

    name: str = Field(..., description="Legal name of the organization")
    slug: str = Field(..., description="Unique URL-friendly identifier")
    billing_email: str = Field(..., description="Email for billing notifications")
    industry: Optional[str] = None
    status: str = Field("active", description="Account status")
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary extension data"
    )


class TenantCreate(TenantBase):
    """Schema for tenant registration."""

    pass


class TenantUpdate(BaseModel):
    """Schema for partial tenant updates."""

    model_config = SCHEMA_MODEL_CONFIG

    name: Optional[str] = None
    billing_email: Optional[str] = None
    status: Optional[str] = None
    extra_metadata: Optional[dict[str, Any]] = None


class Tenant(TenantBase):
    """Full Tenant representation."""

    id: UUID
    created_at: datetime


# Alias for backward compatibility or different naming conventions if needed
TenantSchema = Tenant


class UserBase(BaseModel):
    """Base fields for a User."""

    model_config = SCHEMA_MODEL_CONFIG

    email: EmailStr = Field(..., description="Unique user email address")
    name: Optional[str] = Field(None, description="User's full name")
    role: str = Field("member", description="System role (admin, member, guest)")
    mfa_enabled: bool = Field(False, description="Is multi-factor auth enabled")
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="User UI preferences"
    )


class UserCreate(UserBase):
    """Schema for user registration."""

    tenant_id: UUID
    password_hash: str = Field(..., description="Bcrypt hash of the user's password")


class UserUpdate(BaseModel):
    """Schema for partial user updates."""

    model_config = SCHEMA_MODEL_CONFIG

    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    mfa_enabled: Optional[bool] = None
    preferences: Optional[dict[str, Any]] = None


class User(BaseModel):
    """Full User representation."""

    model_config = SCHEMA_MODEL_CONFIG

    id: UUID
    tenant_id: UUID
    email: EmailStr
    name: Optional[str]
    role: str
    status: str
    mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Alias
UserSchema = User
