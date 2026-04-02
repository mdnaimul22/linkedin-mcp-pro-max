"""Repository layer exports.

Dependency Rule:
    imports FROM: .core, .engine, .profile, .crm, .mcp, .outreach, .trust, .billing
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from .base import BaseRepository

# Core
from .core.plan import PlanRepository
from .core.tenant import TenantRepository
from .core.user import UserRepository

# Engine
from .engine.account import LinkedInAccountRepository
from .engine.event import LinkedInAccountEventRepository
from .engine.profile_global import LinkedInProfileGlobalRepository
from .engine.profile_link import TenantProfileLinkRepository

# Profile
from .profile.experience import ProfileExperienceRepository
from .profile.education import ProfileEducationRepository
from .profile.skill import ProfileSkillRepository

# CRM
from .crm.company import CompanyRepository
from .crm.job_posting import CompanyJobPostingRepository
from .crm.lead import LeadRepository
from .crm.activity import LeadActivityRepository

# MCP
from .mcp.api_key import APIKeyRepository
from .mcp.session import MCPSessionRepository
from .mcp.tool_call import MCPToolCallRepository

# Outreach
from .outreach.template import MessageTemplateRepository
from .outreach.campaign import CampaignRepository
from .outreach.step import CampaignStepRepository
from .outreach.enrollment import CampaignEnrollmentRepository
from .outreach.execution import CampaignStepExecutionRepository

# Trust & Compliance
from .trust.scam_report import ScamReportRepository
from .trust.scam_pattern import ScamPatternRepository
from .trust.audit_log import AuditLogRepository
from .trust.data_request import DataRequestRepository

# Billing
from .billing.subscription import SubscriptionRepository
from .billing.usage import UsageRecordRepository
from .billing.invoice import InvoiceRepository

__all__ = [
    "BaseRepository",
    "PlanRepository",
    "TenantRepository",
    "UserRepository",
    "LinkedInAccountRepository",
    "LinkedInAccountEventRepository",
    "LinkedInProfileGlobalRepository",
    "TenantProfileLinkRepository",
    "ProfileExperienceRepository",
    "ProfileEducationRepository",
    "ProfileSkillRepository",
    "CompanyRepository",
    "CompanyJobPostingRepository",
    "LeadRepository",
    "LeadActivityRepository",
    "APIKeyRepository",
    "MCPSessionRepository",
    "MCPToolCallRepository",
    "MessageTemplateRepository",
    "CampaignRepository",
    "CampaignStepRepository",
    "CampaignEnrollmentRepository",
    "CampaignStepExecutionRepository",
    "ScamReportRepository",
    "ScamPatternRepository",
    "AuditLogRepository",
    "DataRequestRepository",
    "SubscriptionRepository",
    "UsageRecordRepository",
    "InvoiceRepository",
]
