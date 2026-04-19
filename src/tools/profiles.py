import json
import logging
from fastmcp.exceptions import ToolError
from app import get_ctx, mcp
from helpers.exceptions import LinkedInMCPError


logger = logging.getLogger("linkedin-mcp.tools.profiles")


@mcp.tool()
async def get_profile(profile_id: str) -> str:
    """Retrieve a LinkedIn profile including experience, education, and skills.

    Args:
        profile_id: LinkedIn profile ID (username slug) or 'me' for self
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        profile_id = await ctx.profiles.resolve_profile_id(profile_id)
        profile = await ctx.profiles.get_profile(profile_id)
        return json.dumps(profile.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def get_company(company_id: str) -> str:
    """Get company information from LinkedIn.

    Args:
        company_id: LinkedIn company ID or URL slug
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        company = await ctx.profiles.get_company(company_id)
        return json.dumps(company.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def analyze_profile(profile_id: str) -> str:
    """Analyze a LinkedIn profile using AI and provide optimization suggestions.

    Args:
        profile_id: LinkedIn profile ID or 'me' for self
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        if not ctx.profile_analyzer._ai:
            raise ToolError("AI provider not configured. Set ANTHROPIC_API_KEY.")

        profile_id = await ctx.profiles.resolve_profile_id(profile_id)
        profile = await ctx.profiles.get_profile(profile_id)
        analysis = await ctx.profile_analyzer.analyze(profile.model_dump())
        return json.dumps(analysis, indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def update_profile(
    headline: str | None = None,
    summary: str | None = None,
) -> str:
    """Update the authenticated user's LinkedIn profile headline and/or summary.

    Args:
        headline: New profile headline (optional)
        summary: New profile 'About' summary (optional)
    """
    if not headline and not summary:
        raise ToolError("At least one of headline or summary must be provided.")

    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        result = await ctx.browser.update_profile(
            headline=headline, summary=summary
        )

        if result["status"] == "success":
            return f"SUCCESS: {result['message']} (Notify network was OFF)."
        else:
            msg = f"ERROR: {result['message']}"
            if "suggestion" in result and result["suggestion"]:
                msg += f"\nSUGGESTION: {result['suggestion']}"
            return msg
    except Exception as e:
        raise ToolError(f"Error during profile update: {e}")


@mcp.tool()
async def add_experience(
    title: str,
    company: str,
    employment_type: str | None = None,
    location: str | None = None,
    description: str | None = None,
    start_month: str | None = None,
    start_year: str | None = None,
    is_current: bool = True,
) -> str:
    """Add a new experience entry to your LinkedIn profile.

    Args:
        title: Job title (e.g. 'Software Engineer')
        company: Company name
        employment_type: Type (e.g. 'Full-time', 'Contract')
        location: City/Country
        description: Role description
        start_month: Month name (e.g. 'January')
        start_year: Year string (e.g. '2023')
        is_current: Whether this is your current role
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        result = await ctx.browser.upsert_experience(
            title=title,
            company=company,
            employment_type=employment_type,
            location=location,
            description=description,
            start_date_month=start_month,
            start_date_year=start_year,
            is_current=is_current,
        )
        if result["status"] == "success":
            return result["message"]

        # Smart error return with suggestion
        err_msg = f"ERROR: {result['message']}"
        if "suggestion" in result:
            err_msg += f"\nSUGGESTION: {result['suggestion']}"
        return err_msg
    except Exception as e:
        raise ToolError(f"Critical error adding experience: {e}")


@mcp.tool()
async def edit_experience(
    position_id: str,
    title: str,
    company: str,
    description: str | None = None,
    is_current: bool = True,
) -> str:
    """Edit an existing experience entry using its LinkedIn Position ID.

    Args:
        position_id: The ID of the position to edit
        title: New job title
        company: New company name
        description: New description
        is_current: Whether currently working here
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        result = await ctx.browser.upsert_experience(
            position_id=position_id,
            title=title,
            company=company,
            description=description,
            is_current=is_current,
        )
        if result["status"] == "success":
            return result["message"]

        return f"ERROR: {result['message']}\nSUGGESTION: {result.get('suggestion', 'Verify position_id.')}"
    except Exception as e:
        raise ToolError(f"Critical error editing experience: {e}")


@mcp.tool()
async def remove_experience(
    title: str,
    company: str,
) -> str:
    """Remove an experience entry securely using browser automation by matching the exact title and company. No position_id needed.

    Args:
        title: Exact title of the experience to remove (e.g. 'Beta Tester')
        company: Exact company name of the experience to remove (e.g. 'MCP Testing Lab')
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        result = await ctx.browser.remove_experience(company=company, title=title)
        if result["status"] == "success":
            return result["message"]

        return f"ERROR: {result['message']}\nSUGGESTION: Verify that the given company and title appear on your LinkedIn Profile's experience section exactly."
    except Exception as e:
        raise ToolError(f"Critical error removing experience: {e}")


@mcp.tool()
async def manage_skills(
    skill_name: str,
    action: str = "add",
) -> str:
    """Add or delete a skill from your LinkedIn profile.

    Args:
        skill_name: Name of the skill (e.g. 'Python', 'Machine Learning')
        action: 'add' or 'delete'
    """
    if action not in ["add", "delete"]:
        raise ToolError("Action must be either 'add' or 'delete'.")

    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()
        result = await ctx.browser.manage_skills(skill_name=skill_name, action=action)
        if result["status"] == "success":
            return result["message"]

        return f"ERROR: {result['message']}\nSUGGESTION: {result.get('suggestion', 'Check spelling.')}"
    except Exception as e:
        raise ToolError(f"Critical error managing skills: {e}")
