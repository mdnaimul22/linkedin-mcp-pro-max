import logging
import json
from typing import Any, Dict, List, Optional
from app import mcp, get_ctx

logger = logging.getLogger("linkedin-mcp.tools.network")


def prune_log_entry(entry: Dict[str, Any], max_chars: int = 3000) -> Dict[str, Any]:
    """Prune large fields in a log entry to keep tool output concise."""
    # Prune Body
    if "body" in entry and entry["body"]:
        body_str = (
            json.dumps(entry["body"])
            if isinstance(entry["body"], (dict, list))
            else str(entry["body"])
        )
        if len(body_str) > max_chars:
            entry["body"] = body_str[:max_chars] + "... (truncated for context limits)"

    # Prune Post Data
    if "post_data" in entry and entry["post_data"]:
        post_str = str(entry["post_data"])
        if len(post_str) > max_chars:
            entry["post_data"] = (
                post_str[:max_chars] + "... (truncated for context limits)"
            )

    # Prune Headers (optional, but keep it clean)
    if "headers" in entry and entry["headers"]:
        # Only keep internal auth/identity headers for discovery
        keep_headers = [
            "x-li-track",
            "x-restli-protocol-version",
            "csrf-token",
            "content-type",
        ]
        entry["headers"] = {
            k: v for k, v in entry["headers"].items() if k.lower() in keep_headers
        }

    return entry


@mcp.tool()
async def get_network_logs(
    query: Optional[str] = None,
    method: Optional[str] = None,
    status: Optional[int] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search and retrieve recent LinkedIn internal API network logs (last 120s).
    This tool provides 'Discovery Power' by allowing you to search for keywords
    within URLs, request payloads, and response bodies.

    Args:
        query: Search string to match in URL, post data, or response body.
        method: Filter by HTTP method (e.g., GET, POST).
        status: Filter by HTTP status code (e.g., 200, 404).
        limit: Max number of logs to return (1-20, default 20).
    """
    try:
        # Enforce max limit for safety
        limit = max(1, min(limit, 20))

        ctx = await get_ctx()
        await ctx.initialize_browser()
        if not ctx.browser:
            return [{"error": "Browser not initialized"}]

        logs = ctx.browser.sniffer.get_recent_logs(
            limit=limit, query=query, method=method, status=status
        )

        # Prune logs for direct tool output (prevent output.txt redirection)
        pruned_logs = [prune_log_entry(log) for log in logs]
        return pruned_logs
    except Exception as exc:
        logger.error(f"Failed to get network logs: {exc}")
        return [{"error": str(exc)}]


@mcp.tool()
async def execute_linkedin_api(
    method: str,
    url: str,
    body: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Execute an authenticated HTTP request directly to a LinkedIn internal API endpoint.

    This tool is the core of the 'self-healing' architecture. When a DOM-based
    tool stops working (e.g., LinkedIn changed their UI), use get_network_logs to
    discover the working API endpoint, then call it directly via this tool —
    without needing any browser DOM interaction.

    The request is automatically authenticated using the current browser session
    cookies (li-at, JSESSIONID, csrf-token). No manual token handling needed.

    Args:
        method:        HTTP verb: GET, POST, PUT, PATCH, or DELETE.
        url:           Full LinkedIn URL or relative path (e.g. '/voyager/api/ugcPosts').
        body:          Optional JSON request body as a dictionary.
        extra_headers: Optional additional headers to include in the request.

    Returns:
        dict with: success (bool), status (int), url, method, body (response), headers.

    Example workflow (self-healing):
        1. get_network_logs(query='ugcPost', method='POST') → find endpoint
        2. execute_linkedin_api('POST', '/voyager/api/ugcPosts', body={...})
        3. If it works → save_api_pattern(name='create_post', ...)
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()

        if not ctx.api_executor:
            return {"success": False, "error": "API executor not initialized. Browser may not be ready."}

        return await ctx.api_executor.execute(
            method=method,
            url=url,
            body=body,
            extra_headers=extra_headers,
        )
    except Exception as exc:
        logger.error(f"execute_linkedin_api failed: {exc}")
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def save_api_pattern(
    name: str,
    method: str,
    url_path: str,
    description: str,
    body_template: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Save a proven LinkedIn API endpoint pattern to the local cookbook.

    After discovering that an endpoint works via execute_linkedin_api, save it
    here so it can be reused in future sessions without rediscovery. The cookbook
    persists on disk at .browser/data/api_cookbook.json.

    Args:
        name:          Unique short identifier for this pattern (e.g. 'create_ugc_post').
        method:        HTTP verb used (GET, POST, etc.).
        url_path:      The LinkedIn API path (e.g. '/voyager/api/ugcPosts').
        description:   Human-readable explanation of what this endpoint does.
        body_template: An example request body with placeholder values (optional).

    Returns:
        dict confirming the save, with total pattern count.
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()

        if not ctx.api_executor:
            return {"saved": False, "error": "API executor not initialized."}

        return ctx.api_executor.save_pattern(
            name=name,
            method=method,
            url_path=url_path,
            body_template=body_template,
            description=description,
        )
    except Exception as exc:
        logger.error(f"save_api_pattern failed: {exc}")
        return {"saved": False, "error": str(exc)}


@mcp.tool()
async def list_api_patterns(
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved LinkedIn API endpoint patterns from the cookbook.

    Use this to see what endpoints have already been discovered and verified
    to work. If a DOM-based tool breaks, check this cookbook first — a working
    API pattern may already be saved.

    Args:
        query: Optional keyword to filter results by name, description, or URL path.

    Returns:
        List of saved patterns, each with: name, method, url_path, description,
        body_template, and saved_at timestamp.
    """
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser()

        if not ctx.api_executor:
            return [{"error": "API executor not initialized."}]

        return ctx.api_executor.list_patterns(query=query)
    except Exception as exc:
        logger.error(f"list_api_patterns failed: {exc}")
        return [{"error": str(exc)}]

