"""Database lifecycle and repository gateway.

SINGLE SOURCE OF TRUTH for database access.
Outside world MUST ONLY connect to the DB through this class.

Dependency Rule:
    imports FROM: config.settings, db.tables, db.categories, sqlalchemy
    MUST NOT import: services, api, browser, session, tools, app
"""

import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import get_settings
from db.categories import (
    PlanRepository,
    TenantRepository,
    UserRepository,
    LinkedInAccountRepository,
    LinkedInAccountEventRepository,
    LinkedInProfileGlobalRepository,
    TenantProfileLinkRepository,
    ProfileExperienceRepository,
    ProfileEducationRepository,
    ProfileSkillRepository,
    CompanyRepository,
    CompanyJobPostingRepository,
    LeadRepository,
    LeadActivityRepository,
    APIKeyRepository,
    MCPSessionRepository,
    MCPToolCallRepository,
    MessageTemplateRepository,
    CampaignRepository,
    CampaignStepRepository,
    CampaignEnrollmentRepository,
    CampaignStepExecutionRepository,
    ScamReportRepository,
    ScamPatternRepository,
    AuditLogRepository,
    DataRequestRepository,
    SubscriptionRepository,
    UsageRecordRepository,
    InvoiceRepository,
)

logger = logging.getLogger("linkedin-mcp.db.database")


class DatabaseService:
    """Manager for database engine, session, and repositories."""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        """Initialize the database engine and session factory."""
        # Connection arguments (PostgreSQL specific settings like search_path)
        connect_args = {}
        if not database_url.startswith("sqlite"):
            connect_args["server_settings"] = {
                "search_path": get_settings().database_schema or "public"
            }

        self._engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        # --- Repository Gateway ---
        # Core
        self.plans = PlanRepository()
        self.tenants = TenantRepository()
        self.users = UserRepository()

        # Engine
        self.linkedin_accounts = LinkedInAccountRepository()
        self.linkedin_events = LinkedInAccountEventRepository()
        self.linkedin_profiles = LinkedInProfileGlobalRepository()
        self.tenant_profile_links = TenantProfileLinkRepository()

        # Profile Details
        self.profile_experiences = ProfileExperienceRepository()
        self.profile_education = ProfileEducationRepository()
        self.profile_skills = ProfileSkillRepository()

        # CRM & Leads
        self.companies = CompanyRepository()
        self.job_postings = CompanyJobPostingRepository()
        self.leads = LeadRepository()
        self.lead_activities = LeadActivityRepository()

        # MCP & API
        self.api_keys = APIKeyRepository()
        self.mcp_sessions = MCPSessionRepository()
        self.mcp_tool_calls = MCPToolCallRepository()

        # Outreach
        self.templates = MessageTemplateRepository()
        self.campaigns = CampaignRepository()
        self.campaign_steps = CampaignStepRepository()
        self.enrollments = CampaignEnrollmentRepository()
        self.executions = CampaignStepExecutionRepository()

        # Trust & Safety
        self.scam_reports = ScamReportRepository()
        self.scam_patterns = ScamPatternRepository()

        # Billing
        self.subscriptions = SubscriptionRepository()
        self.usage_records = UsageRecordRepository()
        self.invoices = InvoiceRepository()

        # Compliance
        self.audit_logs = AuditLogRepository()
        self.data_requests = DataRequestRepository()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides an async database session."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Dispose of the database engine."""
        await self._engine.dispose()
        logger.info("Database engine core disposed.")
