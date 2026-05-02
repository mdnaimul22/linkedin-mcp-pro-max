import json
import typing
from typing import Literal
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from app import get_ctx, mcp
from schema import TrackedApplication, StatusType
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "tracker_tool.log", name="linkedin-mcp.tools.tracker")


@mcp.tool()
async def application(
    action: Literal["list", "track", "update"],
    job_id: str | None = None,
    job_title: str = "",
    company: str = "",
    status: str = "",
    notes: str = "",
    url: str = "",
) -> str:
    """Manage tracked job applications locally.

    Args:
        action: 'list', 'track', or 'update',
        job_id: LinkedIn job ID,
        job_title: Job title,
        company: Company name,
        status: Application status (interested/applied/interviewing/offered/rejected/withdrawn). For 'list', filters results.
        notes: Optional notes,
        url: Optional job URL,
        
    allowed_args_for_action = {
        "list": ["status"],
        "track": ["job_id", "job_title", "company", "status", "notes", "url"],
        "update": ["job_id", "status", "notes"]
    }
    """
    try:
        allowed_args = {
            "list": ["status"],
            "track": ["job_id", "job_title", "company", "status", "notes", "url"],
            "update": ["job_id", "status", "notes"]
        }
        provided = []
        if job_id is not None:
            provided.append("job_id")
        if job_title != "":
            provided.append("job_title")
        if company != "":
            provided.append("company")
        if status != "":
            provided.append("status")
        if notes != "":
            provided.append("notes")
        if url != "":
            provided.append("url")
        
        for arg in provided:
            if arg not in allowed_args.get(action, []):
                raise ToolError(f"Argument '{arg}' is not allowed for action '{action}'. Allowed arguments: {allowed_args.get(action, [])}")

        ctx = await get_ctx()
        async with ctx.lock:
            if action == "list":
                apps = await ctx.tracker.list_applications(status or None)
                return json.dumps([a.model_dump() for a in apps], indent=2, default=str)
                
            elif action == "track":
                if not job_id or not job_title or not company:
                    raise ToolError("job_id, job_title, and company are required for 'track' action.")
                status_typed: StatusType = typing.cast(StatusType, status or "interested")
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
                
            elif action == "update":
                if not job_id or not status:
                    raise ToolError("job_id and status are required for 'update' action.")
                status_typed: StatusType = typing.cast(StatusType, status)
                app = await ctx.tracker.update_status(job_id, status_typed, notes)
                return json.dumps(app.model_dump(), indent=2, default=str)
                
            else:
                raise ToolError(f"Unknown action: {action}")
            
    except ValidationError:
        raise ToolError(
            "Invalid status. Must be one of: interested, applied, interviewing, offered, rejected, withdrawn."
        )
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
