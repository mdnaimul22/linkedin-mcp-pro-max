import logging
from typing import Any

from schema import (
    CompanyInfo,
    Profile,
    JobDetails,
)

logger = logging.getLogger("linkedin-mcp.services.helpers.mapping")


def map_profile_api(
    profile_id: str,
    data: dict[str, Any],
    skills_data: list[dict[str, Any]],
    contact_data: dict[str, Any],
) -> Profile:
    """Map raw LinkedIn API JSON to Schema Profile using Pydantic validation."""
    data["profile_id"] = profile_id
    data["_skills_data"] = skills_data
    data["_contact_data"] = contact_data
    return Profile.model_validate(data)


def map_job_details_api(job_id: str, data: dict[str, Any]) -> JobDetails:
    """Map raw LinkedIn API Job JSON to Schema JobDetails using Pydantic validation."""
    data["job_id"] = job_id
    return JobDetails.model_validate(data)


def map_company_api(company_id: str, data: dict[str, Any]) -> CompanyInfo:
    """Map raw LinkedIn API Company JSON to Schema CompanyInfo using Pydantic validation."""
    data["company_id"] = company_id
    return CompanyInfo.model_validate(data)


def map_profile_browser(profile_id: str, data: dict[str, Any]) -> Profile:
    """Map raw dictionary scraped from LinkedIn browser to Schema Profile using Pydantic validation."""
    data["profile_id"] = profile_id
    return Profile.model_validate(data)
