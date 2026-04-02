import json
import logging
from fastmcp.exceptions import ToolError
from app import get_ctx, mcp
from helpers.exceptions import LinkedInMCPError
from schema.jobs import JobSearchFilter

logger = logging.getLogger("linkedin-mcp.tools.jobs")


@mcp.tool()
async def search_jobs(
    keywords: str,
    location: str = "",
    job_type: str = "",
    experience_level: str = "",
    remote: bool = False,
    date_posted: str = "",
    page: int = 1,
    count: int = 20,
) -> str:
    """Search for job listings on LinkedIn with filters.

    Args:
        keywords: Search keywords (job title, skills, company)
        location: Geographic location (city, state, country)
        job_type: Filter by type: FULL_TIME, PART_TIME, CONTRACT, TEMPORARY, INTERNSHIP
        experience_level: Filter: INTERNSHIP, ENTRY_LEVEL, ASSOCIATE, MID_SENIOR, DIRECTOR, EXECUTIVE
        remote: Filter for remote jobs only
        date_posted: Filter by recency: past-24h, past-week, past-month
        page: Page number for pagination (default 1)
        count: Results per page (1-50, default 20)
    """
    try:
        ctx = await get_ctx()
        search_filter = JobSearchFilter(
            keywords=keywords,
            location=location,
            job_type=[job_type] if job_type else None,
            experience_level=[experience_level] if experience_level else None,
            remote=remote or None,
            date_posted=date_posted or None,
        )
        result = await ctx.jobs.search_jobs(
            search_filter, max(page, 1), max(min(count, 50), 1)
        )
        return json.dumps(result, indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def get_job_details(job_id: str) -> str:
    """Get detailed information about a specific LinkedIn job posting.

    Args:
        job_id: LinkedIn job ID
    """
    try:
        ctx = await get_ctx()
        details = await ctx.jobs.get_job_details(job_id)
        return json.dumps(details.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def get_recommended_jobs(count: int = 10) -> str:
    """Get job recommendations from LinkedIn.

    Args:
        count: Number of recommendations (1-25, default 10)
    """
    try:
        ctx = await get_ctx()
        jobs = await ctx.jobs.get_recommended_jobs(max(min(count, 25), 1))
        return json.dumps([j.model_dump() for j in jobs], indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e
