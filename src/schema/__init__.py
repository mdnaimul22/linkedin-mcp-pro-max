"""
LinkedIn Pro MCP Schema Layer.
Partitioned models for Core, Profile, Jobs, Tracking, and Session domains.
"""

from schema.common import SCHEMA_MODEL_CONFIG, Certification, Language, OutputFormat
from schema.core import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantSchema,
    User,
    UserCreate,
    UserUpdate,
    UserSchema,
)
from schema.profile import Experience, Education, Profile, CompanyInfo
from schema.jobs import JobSearchFilter, JobListing, JobDetails
from schema.tracker import (
    StatusType,
    VALID_STATUSES,
    TrackedApplication,
    TrackingConfig,
)
from schema.document import (
    ResumeHeader,
    ResumeExperience,
    ResumeEducation,
    ResumeContent,
    CoverLetterContent,
    GeneratedDocument,
)
from schema.session import SourceState, RuntimeState

__all__ = [
    "SCHEMA_MODEL_CONFIG",
    "Certification",
    "Language",
    "OutputFormat",
    "Tenant",
    "TenantCreate",
    "TenantUpdate",
    "TenantSchema",
    "User",
    "UserCreate",
    "UserUpdate",
    "UserSchema",
    "Experience",
    "Education",
    "Profile",
    "CompanyInfo",
    "JobSearchFilter",
    "JobListing",
    "JobDetails",
    "StatusType",
    "VALID_STATUSES",
    "TrackedApplication",
    "TrackingConfig",
    "ResumeHeader",
    "ResumeExperience",
    "ResumeEducation",
    "ResumeContent",
    "CoverLetterContent",
    "GeneratedDocument",
    "SourceState",
    "RuntimeState",
]
