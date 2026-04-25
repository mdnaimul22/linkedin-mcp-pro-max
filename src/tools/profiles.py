import json
import logging
from fastmcp.exceptions import ToolError
from app import get_ctx, mcp
from helpers.exceptions import LinkedInMCPError
from typing import Literal

logger = logging.getLogger("linkedin-mcp.tools.profiles")


@mcp.tool()
async def profile(
    action: Literal["get", "analyze", "update", "update_cover_image"],
    profile_id: str = "me",
    headline: str | None = None,
    summary: str | None = None,
    image_path: str | None = None,
) -> str:
    """Manage LinkedIn profiles.
    
    Args:
        action: The profile action to perform ('get', 'analyze', 'update', 'update_cover_image').
        profile_id: LinkedIn profile ID (username slug) or 'me' for self (for 'get' and 'analyze').
        headline: New profile headline (for 'update').
        summary: New profile 'About' summary (for 'update').
        image_path: Absolute path to the image file (for 'update_cover_image').
        
    allowed_args_for_action = {
        "get": ["profile_id"],
        "analyze": ["profile_id"],
        "update": ["headline", "summary"],
        "update_cover_image": ["image_path"]
    }
    """
    try:
        allowed_args = {
            "get": ["profile_id"],
            "analyze": ["profile_id"],
            "update": ["headline", "summary"],
            "update_cover_image": ["image_path"]
        }
        provided = []
        if profile_id != "me":
            provided.append("profile_id")
        if headline is not None:
            provided.append("headline")
        if summary is not None:
            provided.append("summary")
        if image_path is not None:
            provided.append("image_path")
        
        for arg in provided:
            if arg not in allowed_args.get(action, []):
                raise ToolError(f"Argument '{arg}' is not allowed for action '{action}'. Allowed arguments: {allowed_args.get(action, [])}")

        ctx = await get_ctx()
        async with ctx.lock:
            await ctx.initialize_browser()
            
            if action == "get":
                profile_id = await ctx.profiles.resolve_profile_id(profile_id)
                p = await ctx.profiles.get_profile(profile_id)
                return json.dumps(p.model_dump(), indent=2, default=str)
                
            elif action == "analyze":
                if not ctx.profile_analyzer._ai:
                    raise ToolError("AI provider not configured. Set ANTHROPIC_API_KEY.")
                profile_id = await ctx.profiles.resolve_profile_id(profile_id)
                p = await ctx.profiles.get_profile(profile_id)
                analysis = await ctx.profile_analyzer.analyze(p.model_dump())
                return json.dumps(analysis, indent=2, default=str)
                
            elif action == "update":
                if not headline and not summary:
                    raise ToolError("At least one of headline or summary must be provided for update.")
                result = {"status": "success", "message": ""}
                msgs = []
                if headline:
                    res_h = await ctx.browser.update_profile_headline(headline)
                    if res_h.get("status") != "success":
                        return f"ERROR: {res_h.get('message', 'Failed to update headline')}"
                    msgs.append(res_h.get("message", "Headline updated"))
                if summary:
                    res_s = await ctx.browser.update_profile_summary(summary)
                    if res_s.get("status") != "success":
                        return f"ERROR: {res_s.get('message', 'Failed to update summary')}"
                    msgs.append(res_s.get("message", "Summary updated"))
                result["message"] = " and ".join(msgs)
                
                if result["status"] == "success":
                    return f"SUCCESS: {result['message']} (Notify network was OFF)."
                else:
                    msg = f"ERROR: {result['message']}"
                    if "suggestion" in result and result["suggestion"]:
                        msg += f"\nSUGGESTION: {result['suggestion']}"
                    return msg
                    
            elif action == "update_cover_image":
                if not image_path:
                    raise ToolError("image_path must be provided for update_cover_image.")
                result = await ctx.browser.update_cover_image(image_path=image_path)
                if result["status"] == "success":
                    return result["message"]
                return f"ERROR: {result['message']}\nSUGGESTION: Ensure the image file exists and is a valid format (JPG/PNG)."
                
            else:
                raise ToolError(f"Unknown action: {action}")
            
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e
    except Exception as e:
        raise ToolError(f"Critical error in profile tool: {e}")


@mcp.tool()
async def company(company_id: str) -> str:
    """Get company information from LinkedIn.

    Args:
        company_id: LinkedIn company ID or URL slug,
    """
    try:
        ctx = await get_ctx()
        async with ctx.lock:
            await ctx.initialize_browser()
            comp = await ctx.profiles.get_company(company_id)
            return json.dumps(comp.model_dump(), indent=2, default=str)
    except LinkedInMCPError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def experience(
    action: Literal["add", "update", "delete"],
    title: str,
    company: str,
    position_id: str | None = None,
    employment_type: str | None = None,
    location: str | None = None,
    description: str | None = None,
    start_month: str | None = None,
    start_year: str | None = None,
    end_month: str | None = None,
    end_year: str | None = None,
    is_current: bool = True,
) -> str:
    """Manage experience entries on your LinkedIn profile.

    Args:
        action: 'add', 'update', or 'delete',
        title: Job title (e.g. 'Software Engineer'),
        company: Company name,
        position_id: The ID of the position (required for 'update'),
        employment_type: Type (e.g. 'Full-time', 'Contract'),
        location: City/Country,
        description: Role description,
        start_month: Month name (e.g. 'January'),
        start_year: Year string (e.g. '2023'),
        end_month: End Month name (e.g. 'December'),
        end_year: End Year string (e.g. '2024'),
        is_current: Whether this is your current role,
        
    allowed_args_for_action = {
        "add": ["title", "company", "employment_type", "location", "description", "start_month", "start_year", "end_month", "end_year", "is_current"],
        "update": ["position_id", "title", "company", "employment_type", "location", "description", "start_month", "start_year", "end_month", "end_year", "is_current"],
        "delete": ["title", "company"]
    }
    """
    try:
        allowed_args = {
            "add": ["title", "company", "employment_type", "location", "description", "start_month", "start_year", "end_month", "end_year", "is_current"],
            "update": ["position_id", "title", "company", "employment_type", "location", "description", "start_month", "start_year", "end_month", "end_year", "is_current"],
            "delete": ["title", "company"]
        }
        provided = []
        if position_id is not None:
            provided.append("position_id")
        if employment_type is not None:
            provided.append("employment_type")
        if location is not None:
            provided.append("location")
        if description is not None:
            provided.append("description")
        if start_month is not None:
            provided.append("start_month")
        if start_year is not None:
            provided.append("start_year")
        if end_month is not None:
            provided.append("end_month")
        if end_year is not None:
            provided.append("end_year")
        if not is_current:
            provided.append("is_current")
        
        for arg in provided:
            if arg not in allowed_args.get(action, []):
                raise ToolError(f"Argument '{arg}' is not allowed for action '{action}'. Allowed arguments: {allowed_args.get(action, [])}")

        ctx = await get_ctx()
        async with ctx.lock:
            await ctx.initialize_browser()
            
            if action in ["add", "update"]:
                if action == "update" and not position_id:
                    raise ToolError("position_id is required for 'update' action.")
                    
                result = await ctx.browser.upsert_experience(
                    position_id=position_id,
                    title=title,
                    company=company,
                    employment_type=employment_type,
                    location=location,
                    description=description,
                    start_date_month=start_month,
                    start_date_year=start_year,
                    end_date_month=end_month,
                    end_date_year=end_year,
                    is_current=is_current,
                )
                if result["status"] == "success":
                    return result["message"]
                    
                err_msg = f"ERROR: {result['message']}"
                if "suggestion" in result:
                    err_msg += f"\nSUGGESTION: {result['suggestion']}"
                return err_msg
                
            elif action == "delete":
                result = await ctx.browser.remove_experience(company=company, title=title)
                if result["status"] == "success":
                    return result["message"]
                return f"ERROR: {result['message']}\nSUGGESTION: Verify that the given company and title appear on your LinkedIn Profile's experience section exactly."
                
            else:
                raise ToolError(f"Unknown action: {action}")
            
    except Exception as e:
        raise ToolError(f"Critical error managing experience: {e}")


@mcp.tool()
async def skills(
    action: Literal["add", "delete"],
    skill_name: str,
) -> str:
    """Manage skills on your LinkedIn profile.

    Args:
        action: 'add' or 'delete',
        skill_name: Name of the skill (e.g. 'Python', 'Machine Learning'),
    """
    try:
        ctx = await get_ctx()
        async with ctx.lock:
            await ctx.initialize_browser()
            result = await ctx.browser.manage_skills(skill_name=skill_name, action=action)
            if result["status"] == "success":
                return result["message"]

            return f"ERROR: {result['message']}\nSUGGESTION: {result.get('suggestion', 'Check spelling.')}"
    except Exception as e:
        raise ToolError(f"Critical error managing skills: {e}")


@mcp.tool()
async def education(
    action: Literal["add"],
    school: str,
    degree: str,
    field_of_study: str | None = None,
    grade: str | None = None,
    start_year: str | None = None,
    end_year: str | None = None,
    description: str | None = None,
) -> str:
    """Manage education entries on your LinkedIn profile.

    Args:
        action: 'add',
        school: School/University name,
        degree: Degree (e.g. 'Bachelor of Science'),
        field_of_study: Field of study (optional),
        grade: Grade/GPA (optional),
        start_year: Start year string (e.g. '2018'),
        end_year: End year string (e.g. '2022'),
        description: Description of your studies (optional),
    """
    allowed_args = {
        "add": ["school", "degree", "field_of_study", "grade", "start_year", "end_year", "description"]
    }
    provided = ["school", "degree"]
    if field_of_study is not None:
        provided.append("field_of_study")
    if grade is not None:
        provided.append("grade")
    if start_year is not None:
        provided.append("start_year")
    if end_year is not None:
        provided.append("end_year")
    if description is not None:
        provided.append("description")
    
    for arg in provided:
        if arg not in allowed_args.get(action, []):
            raise ToolError(f"Argument '{arg}' is not allowed for action '{action}'. Allowed arguments: {allowed_args.get(action, [])}")

    if action != "add":
        raise ToolError("Only 'add' action is currently supported for education.")
        
    try:
        ctx = await get_ctx()
        async with ctx.lock:
            await ctx.initialize_browser()
            result = await ctx.browser.upsert_education(
                school=school,
                degree=degree,
                field_of_study=field_of_study,
                grade=grade,
                start_year=start_year,
                end_year=end_year,
                description=description,
            )
            if result["status"] == "success":
                return result["message"]

            return f"ERROR: {result['message']}\nSUGGESTION: {result.get('suggestion', 'Verify mandatory fields.')}"
    except Exception as e:
        raise ToolError(f"Critical error managing education: {e}")
