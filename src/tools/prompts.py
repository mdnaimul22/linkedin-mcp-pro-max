from app import mcp
from config import Settings, setup_logger
from config.prompts import (
    MCP_JOB_SEARCH_WORKFLOW,
    MCP_APPLICATION_WORKFLOW,
    MCP_PROFILE_OPTIMIZATION,
)

logger = setup_logger(Settings.LOG_DIR / "prompts_tool.log", name="linkedin-mcp.tools.prompts")


@mcp.prompt()
async def job_search_workflow(role: str, location: str = "") -> str:
    """Guide through searching for jobs, reviewing listings, and tracking applications."""
    return MCP_JOB_SEARCH_WORKFLOW.format(role=role, loc=f" in {location}" if location else "")


@mcp.prompt()
async def application_workflow(job_id: str) -> str:
    """Guide through preparing a complete application for a specific job."""
    return MCP_APPLICATION_WORKFLOW.format(job_id=job_id)


@mcp.prompt()
async def profile_optimization() -> str:
    """Guide through optimizing a LinkedIn profile."""
    return MCP_PROFILE_OPTIMIZATION
