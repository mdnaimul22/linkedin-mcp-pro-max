import json
import logging
import typing
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from app import get_ctx, mcp
from schema.tracker import TrackedApplication, StatusType

logger = logging.getLogger("linkedin-mcp.tools.tracker")


@mcp.tool()
async def track_application(
    job_id: str,
    job_title: str,
    company: str,
    status: str = "interested",
    notes: str = "",
    url: str = "",
) -> str:
    """Track a job application locally. Status: interested, applied, interviewing, offered, rejected, withdrawn.

    Args:
        job_id: LinkedIn job ID
        job_title: Job title
        company: Company name
        status: Application status (interested/applied/interviewing/offered/rejected/withdrawn)
        notes: Optional notes
        url: Optional job URL
    """
    try:
        status_typed: StatusType = typing.cast(StatusType, status)
        ctx = await get_ctx()
        app = TrackedApplication(
            job_id=job_id,
            job_title=job_title,
            company=company,
            status=status_typed,
            notes=notes,
            url=url,
        )
        result = await ctx.tracker.track_application(app)
        return json.dumps(result.model_dump(), indent=2, default=str)
    except ValidationError:
        raise ToolError(
            "Invalid status. Must be one of: interested, applied, interviewing, offered, rejected, withdrawn."
        )
    except Exception as e:
        raise ToolError(str(e))


@mcp.tool()
async def list_applications(status: str = "") -> str:
    """List tracked job applications."""
    try:
        ctx = await get_ctx()
        apps = await ctx.tracker.list_applications(status or None)
        return json.dumps([a.model_dump() for a in apps], indent=2, default=str)
    except Exception as e:
        raise ToolError(str(e))


@mcp.tool()
async def update_application_status(job_id: str, status: str, notes: str = "") -> str:
    """Update the status of a tracked job application.

    Args:
        job_id: LinkedIn job ID
        status: New status (interested, applied, interviewing, offered, rejected, withdrawn)
        notes: Optional notes about the update
    """
    try:
        ctx = await get_ctx()
        status_typed: StatusType = typing.cast(StatusType, status)
        app = await ctx.tracker.update_status(job_id, status_typed, notes)
        return json.dumps(app.model_dump(), indent=2, default=str)
    except ValidationError:
        raise ToolError("Invalid status.")
    except Exception as e:
        raise ToolError(str(e))


@mcp.resource("linkedin://applications")
async def applications_resource() -> str:
    """Summary of tracked job applications."""
    try:
        ctx = await get_ctx()
        apps = await ctx.tracker.list_applications()
        summary = {
            "total": len(apps),
            "by_status": {},
            "applications": [a.model_dump() for a in apps],
        }
        for app in apps:
            summary["by_status"][app.status] = (
                summary["by_status"].get(app.status, 0) + 1
            )
        return json.dumps(summary, indent=2, default=str)
    except Exception:
        return json.dumps({"error": "Failed to load", "total": 0})
