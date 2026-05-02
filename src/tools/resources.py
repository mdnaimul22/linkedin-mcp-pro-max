import json
from app import get_ctx, mcp
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "tool.log", name="linkedin-mcp.tools.resources")


@mcp.resource("linkedin://profile/{profile_id}")
async def profile_resource(profile_id: str) -> str:
    """Retrieve a cached LinkedIn profile."""
    try:
        ctx = await get_ctx()
        profile_id = await ctx.profiles.resolve_profile_id(profile_id)
        profile = await ctx.profiles.get_profile(profile_id)
        return json.dumps(profile.model_dump(), indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to load profile resource: {e}")
        return json.dumps({"error": str(e)})


@mcp.resource("linkedin://job/{job_id}")
async def job_resource(job_id: str) -> str:
    """Retrieve cached job details."""
    try:
        ctx = await get_ctx()
        job = await ctx.jobs.get_job_details(job_id)
        return json.dumps(job.model_dump(), indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to load job resource: {e}")
        return json.dumps({"error": str(e)})
