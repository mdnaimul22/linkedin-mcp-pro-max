import json
from typing import Literal, Any, Optional
from fastmcp.exceptions import ToolError
from app import get_ctx, mcp
from schema import JobSearchFilter
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "jobs_tool.log", name="linkedin-mcp.tools.jobs")


@mcp.tool()
async def job(
    action: Literal["search", "details", "recommended", "apply"],
    job_id: str | None = None,
    keywords: str | None = None,
    location: str = "",
    job_type: str = "",
    experience_level: str = "",
    remote: bool = False,
    date_posted: str = "",
    page: int = 1,
    count: int = 20,
) -> str:
    """Discover and manage LinkedIn job postings.

    Args:
        action: 'search', 'details', 'recommended', or 'apply',
        job_id: LinkedIn job ID (required for 'details' and 'apply'),
        keywords: Search keywords (job title, skills, company),
        location: Geographic location (city, state, country),
        job_type: Filter by type: FULL_TIME, PART_TIME, CONTRACT, TEMPORARY, INTERNSHIP,
        experience_level: Filter: INTERNSHIP, ENTRY_LEVEL, ASSOCIATE, MID_SENIOR, DIRECTOR, EXECUTIVE,
        remote: Filter for remote jobs only,
        date_posted: Filter by recency: past-24h, past-week, past-month,
        page: Page number for pagination (default 1),
        count: Results per page (1-50, default 20),
        
    allowed_args_for_action = {
        "search": ["keywords", "location", "job_type", "experience_level", "remote", "date_posted", "page", "count"],
        "details": ["job_id"],
        "recommended": ["count"],
        "apply": ["job_id"]
    }
    """
    try:
        allowed_args = {
            "search": ["keywords", "location", "job_type", "experience_level", "remote", "date_posted", "page", "count"],
            "details": ["job_id"],
            "recommended": ["count"],
            "apply": ["job_id"]
        }
        provided = []
        if job_id is not None:
            provided.append("job_id")
        if keywords is not None:
            provided.append("keywords")
        if location != "":
            provided.append("location")
        if job_type != "":
            provided.append("job_type")
        if experience_level != "":
            provided.append("experience_level")
        if remote:
            provided.append("remote")
        if date_posted != "":
            provided.append("date_posted")
        if page != 1:
            provided.append("page")
        if count != 20:
            provided.append("count")
        
        for arg in provided:
            if arg not in allowed_args.get(action, []):
                raise ToolError(f"Argument '{arg}' is not allowed for action '{action}'. Allowed arguments: {allowed_args.get(action, [])}")

        ctx = await get_ctx()
        async with ctx.lock:
            if action == "search":
                if not keywords:
                    raise ToolError("keywords argument is required for 'search' action.")
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
                
            elif action == "details":
                if not job_id:
                    raise ToolError("job_id is required for 'details' action.")
                details = await ctx.jobs.get_job_details(job_id)
                return json.dumps(details.model_dump(), indent=2, default=str)
                
            elif action == "recommended":
                jobs = await ctx.jobs.get_recommended_jobs(max(min(count, 25), 1))
                return json.dumps([j.model_dump() for j in jobs], indent=2, default=str)
                
            elif action == "apply":
                if not job_id:
                    raise ToolError("job_id is required for 'apply' action.")
                # Assume future implementation or basic prompt return if not directly available yet
                raise ToolError("Direct apply through MCP is not fully implemented. Please use 'track_application' instead.")
                
            else:
                raise ToolError(f"Unknown action: {action}")
            
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e
