import json
from fastmcp.exceptions import ToolError
from app import get_ctx, mcp
from helpers.exceptions import LinkedInMCPError
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "tool.log", name="linkedin-mcp.tools.resume")

_VALID_FORMATS = {"html", "md", "pdf"}


def _validate_format(output_format: str) -> None:
    """Raise ToolError if format is invalid."""
    if output_format not in _VALID_FORMATS:
        raise ToolError(
            f"Invalid format '{output_format}'. Must be one of: {sorted(_VALID_FORMATS)}"
        )


@mcp.tool()
async def generate_resume(
    profile_id: str, template: str = "modern", output_format: str = "html"
) -> str:
    """Generate a professional resume from a LinkedIn profile using AI enhancement.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
        template: Template name (modern, professional)
        output_format: Output format (html, md, pdf)
    """
    _validate_format(output_format)
    try:
        ctx = await get_ctx()
        profile_id = await ctx.profiles.resolve_profile_id(profile_id)
        doc = await ctx.resume_gen.generate_resume(
            profile_id, template, output_format
        )
        if output_format == "pdf":
            return json.dumps(
                {"format": "pdf", "file_path": doc.file_path, "metadata": doc.metadata}
            )
        return doc.content
    except (LinkedInMCPError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def tailor_resume(
    profile_id: str, job_id: str, template: str = "modern", output_format: str = "html"
) -> str:
    """Generate a resume tailored to a specific job posting.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
        job_id: LinkedIn job ID to tailor the resume for
        template: Template name (modern, professional)
        output_format: Output format (html, md, pdf)
    """
    _validate_format(output_format)
    try:
        ctx = await get_ctx()
        profile_id = await ctx.profiles.resolve_profile_id(profile_id)
        doc = await ctx.resume_gen.tailor_resume(
            profile_id, job_id, template, output_format
        )
        if output_format == "pdf":
            return json.dumps(
                {"format": "pdf", "file_path": doc.file_path, "metadata": doc.metadata}
            )
        return doc.content
    except (LinkedInMCPError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def generate_cover_letter(
    profile_id: str,
    job_id: str,
    template: str = "professional",
    output_format: str = "html",
) -> str:
    """Generate a personalized cover letter for a specific job posting.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
        job_id: LinkedIn job ID
        template: Template name (professional, concise)
        output_format: Output format (html, md, pdf)
    """
    _validate_format(output_format)
    try:
        ctx = await get_ctx()
        profile_id = await ctx.profiles.resolve_profile_id(profile_id)
        doc = await ctx.cover_letter_gen.generate_cover_letter(
            profile_id, job_id, template, output_format
        )
        if output_format == "pdf":
            return json.dumps(
                {"format": "pdf", "file_path": doc.file_path, "metadata": doc.metadata}
            )
        return doc.content
    except (LinkedInMCPError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def list_templates(template_type: str = "all") -> str:
    """List all available templates for resumes and cover letters.

    Args:
        template_type: Template type to list: 'resume', 'cover_letter', or 'all'
    """
    if template_type not in ("resume", "cover_letter", "all"):
        raise ToolError(
            f"Invalid template_type '{template_type}'. Must be 'resume', 'cover_letter', or 'all'."
        )
    ctx = await get_ctx()
    result = {}
    if template_type in ("resume", "all"):
        result["resume"] = ctx.resume_gen.list_templates()
    if template_type in ("cover_letter", "all"):
        result["cover_letter"] = ctx.cover_letter_gen.list_templates()
    return json.dumps(result, indent=2)
