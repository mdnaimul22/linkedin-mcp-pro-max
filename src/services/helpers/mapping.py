"""Mapping utilities between Source Data (API, Browser, DB) and Pydantic Schemas.

This module acts as a bridge between Level 2 (Infrastructure) and Level 1 (Schema).
It ensures that the Service Layer (Level 3) always receives standardized Domain Models.

Dependency Rule:
    imports FROM: schema, db.tables
    MUST NOT import: api, browser, session, providers, tools, config
"""

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from schema import (
    Certification,
    CompanyInfo,
    Education,
    Experience,
    Language,
    Profile,
    JobDetails,
)
from db.tables import (
    Company,
    LinkedInProfileGlobal,
    ProfileEducation,
    ProfileExperience,
    ProfileSkill,
)

logger = logging.getLogger("linkedin-mcp.services.helpers.mapping")


# --- Internal Helpers ---


def _format_timestamp(value: Any) -> str:
    """Convert LinkedIn millisecond timestamp to ISO date string."""
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
    return str(value) if value else ""


def _format_date_obj(date_obj: dict[str, Any] | None) -> str:
    """Format LinkedIn date object {month, year} to 'Jan 2020' string."""
    if not date_obj:
        return ""
    month = date_obj.get("month", 0)
    year = date_obj.get("year", 0)
    if month and year:
        months = [
            "",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        return f"{months[min(month, 12)]} {year}"
    return str(year) if year else ""


# --- DB to Schema Mappings ---


def map_experience_db(record: ProfileExperience) -> Experience:
    """Map DB ProfileExperience to Schema Experience."""
    return Experience(
        title=record.title or "",
        company=record.company_name or "",
        location=record.location or "",
        start_date=record.started_at.strftime("%Y-%m-%d") if record.started_at else "",
        end_date=record.ended_at.strftime("%Y-%m-%d")
        if record.ended_at
        else ("Present" if record.is_current else ""),
        description=record.description or "",
    )


def map_education_db(record: ProfileEducation) -> Education:
    """Map DB ProfileEducation to Schema Education."""
    return Education(
        school=record.institution or "",
        degree=record.degree or "",
        field_of_study=record.field_of_study or "",
        start_date=record.started_at.strftime("%Y-%m-%d") if record.started_at else "",
        end_date=record.ended_at.strftime("%Y-%m-%d") if record.ended_at else "",
    )


def map_profile_db(
    profile: LinkedInProfileGlobal,
    experiences: Optional[List[ProfileExperience]] = None,
    education: Optional[List[ProfileEducation]] = None,
    skills: Optional[List[ProfileSkill]] = None,
) -> Profile:
    """Map DB LinkedInProfileGlobal and its relations to Schema Profile."""
    # Deduplicate experiences
    seen_exp = set()
    exp_list = []
    for e in (experiences or []):
        exp = map_experience_db(e)
        identifier = (exp.title, exp.company, exp.start_date, exp.end_date)
        if identifier not in seen_exp:
            seen_exp.add(identifier)
            exp_list.append(exp)

    edu_list = [map_education_db(e) for e in (education or [])]

    # Deduplicate skills
    seen_skills = set()
    skill_list = []
    for s in (skills or []):
        if s.skill_name and s.skill_name not in seen_skills:
            seen_skills.add(s.skill_name)
            skill_list.append(s.skill_name)

    return Profile(
        profile_id=profile.linkedin_id or profile.profile_url,
        name=profile.full_name
        or f"{profile.first_name or ''} {profile.last_name or ''}".strip(),
        headline=profile.headline or "",
        summary=profile.summary or "",
        location=profile.location or "",
        industry=profile.industry or "",
        email=profile.email or "",
        phone=profile.phone or "",
        profile_url=profile.profile_url,
        experience=exp_list,
        education=edu_list,
        skills=skill_list,
        certifications=[],
        languages=[],
    )


def map_company_db(record: Company) -> CompanyInfo:
    """Map DB Company to Schema CompanyInfo."""
    return CompanyInfo(
        company_id=record.linkedin_id or str(record.id),
        name=record.name,
        tagline="",
        description=record.description or "",
        website=record.website or "",
        industry=record.industry or "",
        company_size=record.company_size or "",
        headquarters=record.headquarters or "",
        specialties=record.specialties or [],
        url=record.linkedin_url or "",
    )


# --- API (JSON) to Schema Mappings ---


def map_profile_api(
    profile_id: str,
    data: dict[str, Any],
    skills_data: list[dict[str, Any]],
    contact_data: dict[str, Any],
) -> Profile:
    """Map raw LinkedIn API JSON to Schema Profile."""
    experience = [
        Experience(
            title=exp.get("title", ""),
            company=exp.get("companyName", ""),
            location=exp.get("locationName", ""),
            start_date=_format_date_obj(exp.get("timePeriod", {}).get("startDate")),
            end_date=(
                _format_date_obj(exp.get("timePeriod", {}).get("endDate"))
                if exp.get("timePeriod", {}).get("endDate")
                else "Present"
            ),
            description=exp.get("description", ""),
        )
        for exp in data.get("experience", [])
    ]

    education = [
        Education(
            school=edu.get("schoolName", ""),
            degree=edu.get("degreeName", ""),
            field_of_study=edu.get("fieldOfStudy", ""),
            start_date=_format_date_obj(edu.get("timePeriod", {}).get("startDate")),
            end_date=_format_date_obj(edu.get("timePeriod", {}).get("endDate")),
        )
        for edu in data.get("education", [])
    ]

    return Profile(
        profile_id=profile_id,
        name=f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
        headline=data.get("headline", ""),
        summary=data.get("summary", ""),
        location=data.get("locationName", ""),
        industry=data.get("industryName", ""),
        email=contact_data.get("email_address", ""),
        phone=(
            ", ".join(contact_data.get("phone_numbers", []))
            if contact_data.get("phone_numbers")
            else ""
        ),
        profile_url=f"https://www.linkedin.com/in/{profile_id}",
        experience=experience,
        education=education,
        skills=[s.get("name", "") for s in skills_data if s.get("name")],
        languages=[
            Language(name=lang.get("name", ""), proficiency=lang.get("proficiency", ""))
            for lang in data.get("languages", [])
        ],
        certifications=[
            Certification(
                name=cert.get("name", ""), authority=cert.get("authority", "")
            )
            for cert in data.get("certifications", [])
        ],
    )


def map_job_details_api(job_id: str, data: dict[str, Any]) -> JobDetails:
    """Map raw LinkedIn API Job JSON to Schema JobDetails."""
    job = data.get("jobDetails", data)
    description = job.get("description", {}).get("text", "")

    # Extract skills if present (often in a subfield)
    skills = []
    if "skills" in job:
        skills = [s.get("name", "") for s in job["skills"] if s.get("name")]

    return JobDetails(
        job_id=job_id,
        title=job.get("title", ""),
        company=job.get("companyDetails", {}).get(
            "company", job.get("companyName", "Unknown")
        ),
        location=job.get("formattedLocation", job.get("location", "")),
        description=description if isinstance(description, str) else "",
        url=f"https://www.linkedin.com/jobs/view/{job_id}",
        employment_type=job.get("employmentType", ""),
        seniority_level=job.get("seniorityLevel", ""),
        skills=skills,
        industries=job.get("industries", []),
        job_functions=job.get("jobFunctions", []),
        date_posted=_format_timestamp(job.get("listedAt", "")),
        applicant_count=job.get("applicantCount"),
    )


def map_company_api(company_id: str, data: dict[str, Any]) -> CompanyInfo:
    """Map raw LinkedIn API Company JSON to Schema CompanyInfo."""
    hq = data.get("headquarter", {})
    parts = [hq.get("city", ""), hq.get("geographicArea", ""), hq.get("country", "")]
    headquarters = ", ".join(p for p in parts if p)

    industry = data.get("industryName", "")
    if not industry and data.get("companyIndustries"):
        industry = data["companyIndustries"][0].get("localizedName", "")

    return CompanyInfo(
        company_id=company_id,
        name=data.get("name", ""),
        tagline=data.get("tagline", ""),
        description=data.get("description", ""),
        website=data.get("companyPageUrl", data.get("website", "")),
        industry=industry,
        company_size=f"{data.get('staffCount', 'Unknown')} employees",
        headquarters=headquarters,
        specialties=data.get("specialities", data.get("specialties", [])),
        url=f"https://www.linkedin.com/company/{company_id}",
    )


# --- Browser Scraped Data to Schema Mappings ---


def map_profile_browser(profile_id: str, data: dict[str, Any]) -> Profile:
    """Map raw dictionary scraped from LinkedIn browser to Schema Profile."""
    exp_list = [
        Experience(
            title=e.get("title", ""),
            company=e.get("company", ""),
            location=e.get("location", ""),
            start_date=e.get("start_date", ""),
            end_date=e.get("end_date", "Present"),
            description=e.get("description", ""),
        )
        for e in data.get("experience", [])
    ]

    edu_list = [
        Education(
            school=e.get("school", ""),
            degree=e.get("degree", ""),
            field_of_study=e.get("field_of_study", ""),
            start_date=e.get("start_date", ""),
            end_date=e.get("end_date", ""),
        )
        for e in data.get("education", [])
    ]

    return Profile(
        profile_id=profile_id,
        name=data.get("name", "Unknown"),
        headline=data.get("headline", ""),
        summary=data.get("summary", ""),
        location=data.get("location", ""),
        industry=data.get("industry", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        profile_url=data.get(
            "profile_url", f"https://www.linkedin.com/in/{profile_id}"
        ),
        experience=exp_list,
        education=edu_list,
        skills=data.get("skills", []),
        certifications=[
            Certification(name=c.get("name", ""), authority=c.get("authority", ""))
            for c in data.get("certifications", [])
        ],
        languages=[
            Language(name=lang.get("name", ""), proficiency=lang.get("proficiency", ""))
            for lang in data.get("languages", [])
        ],
    )
