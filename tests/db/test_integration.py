import pytest
from src.db.database import DatabaseService
from src.db.categories import (
    PlanRepository, TenantRepository, UserRepository,
    LinkedInAccountRepository, LinkedInAccountEventRepository,
    LinkedInProfileGlobalRepository, TenantProfileLinkRepository,
    ProfileExperienceRepository, ProfileEducationRepository, ProfileSkillRepository,
    CompanyRepository, CompanyJobPostingRepository, LeadRepository, LeadActivityRepository,
    APIKeyRepository, MCPSessionRepository, MCPToolCallRepository,
    MessageTemplateRepository, CampaignRepository, CampaignStepRepository,
    CampaignEnrollmentRepository, CampaignStepExecutionRepository,
    ScamReportRepository, ScamPatternRepository,
    SubscriptionRepository, UsageRecordRepository, InvoiceRepository,
    AuditLogRepository, DataRequestRepository
)

@pytest.mark.asyncio
async def test_database_service_initialization(db_service: DatabaseService):
    """Verify that all 29 repositories are correctly initialized in DatabaseService."""
    
    # Core
    assert isinstance(db_service.plans, PlanRepository)
    assert isinstance(db_service.tenants, TenantRepository)
    assert isinstance(db_service.users, UserRepository)
    
    # Engine
    assert isinstance(db_service.linkedin_accounts, LinkedInAccountRepository)
    assert isinstance(db_service.linkedin_events, LinkedInAccountEventRepository)
    assert isinstance(db_service.linkedin_profiles, LinkedInProfileGlobalRepository)
    assert isinstance(db_service.tenant_profile_links, TenantProfileLinkRepository)
    
    # Profile Details
    assert isinstance(db_service.profile_experiences, ProfileExperienceRepository)
    assert isinstance(db_service.profile_education, ProfileEducationRepository)
    assert isinstance(db_service.profile_skills, ProfileSkillRepository)
    
    # CRM & Leads
    assert isinstance(db_service.companies, CompanyRepository)
    assert isinstance(db_service.job_postings, CompanyJobPostingRepository)
    assert isinstance(db_service.leads, LeadRepository)
    assert isinstance(db_service.lead_activities, LeadActivityRepository)
    
    # MCP & API
    assert isinstance(db_service.api_keys, APIKeyRepository)
    assert isinstance(db_service.mcp_sessions, MCPSessionRepository)
    assert isinstance(db_service.mcp_tool_calls, MCPToolCallRepository)
    
    # Outreach
    assert isinstance(db_service.templates, MessageTemplateRepository)
    assert isinstance(db_service.campaigns, CampaignRepository)
    assert isinstance(db_service.campaign_steps, CampaignStepRepository)
    assert isinstance(db_service.enrollments, CampaignEnrollmentRepository)
    assert isinstance(db_service.executions, CampaignStepExecutionRepository)
    
    # Trust & Safety
    assert isinstance(db_service.scam_reports, ScamReportRepository)
    assert isinstance(db_service.scam_patterns, ScamPatternRepository)
    
    # Billing
    assert isinstance(db_service.subscriptions, SubscriptionRepository)
    assert isinstance(db_service.usage_records, UsageRecordRepository)
    assert isinstance(db_service.invoices, InvoiceRepository)
    
    # Compliance
    assert isinstance(db_service.audit_logs, AuditLogRepository)
    assert isinstance(db_service.data_requests, DataRequestRepository)

@pytest.mark.asyncio
async def test_database_get_session(db_service: DatabaseService):
    """Verify that get_session context manager works."""
    async with db_service.get_session() as session:
        assert session is not None
        # Verify it's an active session
        assert session.is_active is True
