"""SQLAlchemy models for enterprise_saas schema.

Dependency Rule:
    imports FROM: config, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    BOOLEAN,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.types import UserDefinedType
from sqlalchemy.dialects.postgresql import ARRAY, INET, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config.settings import get_settings

import logging

logger = logging.getLogger("linkedin-mcp.db.tables")


def _resolve_schema() -> str | None:
    """Resolve the database schema lazily to avoid import-time side effects."""
    s = get_settings().database_schema
    return None if s == "public" else s


metadata_obj = MetaData(schema=_resolve_schema())


class Base(DeclarativeBase):
    """Base class for all models."""

    metadata = metadata_obj


class Vector(UserDefinedType):
    """Custom type for PostgreSQL pgvector compatibility."""

    def get_col_spec(self, **kw):
        return "vector(1536)"


class Plan(Base):
    """
    PLANS table (define first — tenants FK to this).
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "plans"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_monthly: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_yearly: Mapped[float | None] = mapped_column(Numeric(10, 2))
    limits: Mapped[dict] = mapped_column(JSON, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool | None] = mapped_column(BOOLEAN, default=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Tenant(Base):
    """
    TENANTS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(30), default="active")
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    billing_email: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class User(Base):
    """
    USERS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), default="member")
    status: Mapped[str | None] = mapped_column(String(20), default="active")
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool | None] = mapped_column(BOOLEAN, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferences: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LinkedInAccount(Base):
    """
    LINKEDIN_ACCOUNTS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "linkedin_accounts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    linkedin_member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # oauth, cookie, api_key
    is_tos_compliant: Mapped[bool | None] = mapped_column(
        BOOLEAN, nullable=True
    )  # Generated in DB
    oauth_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    cookie_session: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    token_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    token_refresh_count: Mapped[int | None] = mapped_column(Integer, default=0)
    account_status: Mapped[str | None] = mapped_column(String(30), default="connected")
    health_score: Mapped[int | None] = mapped_column(SmallInteger, default=100)
    daily_connections_sent: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    daily_messages_sent: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    daily_profile_views: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    daily_searches: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    limits_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LinkedInAccountEvent(Base):
    """
    LINKEDIN_ACCOUNT_EVENTS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "linkedin_account_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_accounts.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LinkedInProfileGlobal(Base):
    """
    LINKEDIN_PROFILES_GLOBAL table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "linkedin_profiles_global"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    linkedin_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    profile_url: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    vanity_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    current_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    connection_degree: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    connection_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector, nullable=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetch_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_quality_score: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TenantProfileLink(Base):
    """
    TENANT_PROFILE_LINKS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "tenant_profile_links"

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("linkedin_profiles_global.id"),
        primary_key=True,
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    custom_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    tenant_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    added_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ProfileExperience(Base):
    """
    PROFILE_EXPERIENCES table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "profile_experiences"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_profiles_global.id"), nullable=False
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_li_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool | None] = mapped_column(BOOLEAN, default=False)
    duration_months: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class ProfileEducation(Base):
    """
    PROFILE_EDUCATION table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "profile_education"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_profiles_global.id"), nullable=False
    )
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(Date, nullable=True)


class ProfileSkill(Base):
    """
    PROFILE_SKILLS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "profile_skills"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_profiles_global.id"), nullable=False
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    endorsement_count: Mapped[int | None] = mapped_column(Integer, default=0)


class Company(Base):
    """
    COMPANIES table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    linkedin_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    founded_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    specialties: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hiring_signal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recent_job_posts: Mapped[int | None] = mapped_column(Integer, default=0)
    funding_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_revenue: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tech_stack: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    risk_flags: Mapped[list | None] = mapped_column(JSON, default=list)
    raw_data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector, nullable=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CompanyJobPosting(Base):
    """
    COMPANY_JOB_POSTINGS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "company_job_postings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool | None] = mapped_column(BOOLEAN, default=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, default=dict)


class Lead(Base):
    """
    LEADS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_profiles_global.id"), nullable=True
    )
    company_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    assigned_to: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    lead_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), default="new")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lead_score: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, default=dict)
    estimated_loan_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    loan_purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creditworthiness_tier: Mapped[str | None] = mapped_column(String(1), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    custom_fields: Mapped[dict | None] = mapped_column(JSON, default=dict)
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_followup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LeadActivity(Base):
    """
    LEAD_ACTIVITIES table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "lead_activities"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class APIKey(Base):
    """
    API_KEYS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    rate_limit_rpm: Mapped[int | None] = mapped_column(Integer, default=60)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool | None] = mapped_column(BOOLEAN, default=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MCPSession(Base):
    """
    MCP_SESSIONS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "mcp_sessions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    api_key_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True
    )
    client_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    protocol_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), default="active")
    ping_interval_secs: Mapped[int | None] = mapped_column(Integer, default=30)
    missed_pings: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_ping_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)


class MCPToolCall(Base):
    """
    MCP_TOOL_CALLS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "mcp_tool_calls"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("mcp_sessions.id"), nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_truncated: Mapped[bool | None] = mapped_column(BOOLEAN, default=False)
    status: Mapped[str | None] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    linkedin_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_accounts.id"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class MessageTemplate(Base):
    """
    MESSAGE_TEMPLATES table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "message_templates"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    ai_personalize: Mapped[bool | None] = mapped_column(BOOLEAN, default=False)
    performance_stats: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Campaign(Base):
    """
    CAMPAIGNS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), default="draft")
    target_filters: Mapped[dict | None] = mapped_column(JSON, default=dict)
    daily_limit: Mapped[int | None] = mapped_column(Integer, default=20)
    total_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CampaignStep(Base):
    """
    CAMPAIGN_STEPS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "campaign_steps"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)
    delay_hours: Mapped[int | None] = mapped_column(Integer, default=0)
    template_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("message_templates.id"), nullable=True
    )
    condition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CampaignEnrollment(Base):
    """
    CAMPAIGN_ENROLLMENTS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "campaign_enrollments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False
    )
    current_step: Mapped[int | None] = mapped_column(SmallInteger, default=0)
    status: Mapped[str | None] = mapped_column(String(50), default="active")
    enrolled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CampaignStepExecution(Base):
    """
    CAMPAIGN_STEP_EXECUTIONS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "campaign_step_executions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("campaign_enrollments.id"), nullable=False
    )
    step_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("campaign_steps.id"), nullable=False
    )
    status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # sent, failed, skipped
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ScamReport(Base):
    """
    SCAM_REPORTS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "scam_reports"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    reported_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("linkedin_profiles_global.id"), nullable=True
    )
    company_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    detection_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    flags: Mapped[list | None] = mapped_column(JSON, default=list)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), default="open")
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ScamPattern(Base):
    """
    SCAM_PATTERNS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "scam_patterns"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    pattern_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    pattern_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(BOOLEAN, default=True)
    hit_count: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Subscription(Base):
    """
    SUBSCRIPTIONS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), default="active")
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class UsageRecord(Base):
    """
    USAGE_RECORDS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "usage_records"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int | None] = mapped_column(BigInteger, default=0)
    limit_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Invoice(Base):
    """
    INVOICES table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    stripe_invoice_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    amount_due: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount_paid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), default="USD")
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AuditLog(Base):
    """
    AUDIT_LOGS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DataRequest(Base):
    """
    DATA_REQUESTS table.
    Verified against docs/db_schema.md and live Supabase.
    """

    __tablename__ = "data_requests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), default="pending")
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
