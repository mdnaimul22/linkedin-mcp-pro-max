"""API Executor Service — Authenticated LinkedIn Internal API Gateway.

Allows the AI to make raw, authenticated HTTP requests to LinkedIn's internal
API endpoints discovered via the NetworkSniffer, bypassing DOM/browser UI.

This is the core of the "Self-Healing" architecture: when a DOM-based tool
breaks, the AI can discover the working endpoints via get_network_logs and
call them directly using this service, without any UI dependency.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from patchright.async_api import Page

logger = logging.getLogger("linkedin-mcp.api.executor")


class ApiExecutor:
    """Execute raw authenticated requests to LinkedIn's internal API.

    Uses Playwright's browser context to make requests that automatically
    carry the authenticated session cookies (li-at, JSESSIONID, csrf-token).
    This means every request is fully authenticated — no manual token
    management needed.

    Pattern Registry:
        Proven endpoint patterns can be saved to a local JSON "cookbook"
        so the AI can rediscover and reuse them in future sessions.
    """

    def __init__(self, page: Page, registry_path: Path) -> None:
        self._page = page
        self._registry_path = registry_path
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Raw API Execution
    # -------------------------------------------------------------------------

    async def execute(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated HTTP request via the browser session.

        Args:
            method:        HTTP verb (GET, POST, PUT, DELETE, PATCH).
            url:           Full URL or LinkedIn-relative path (e.g. /voyager/api/...).
            body:          Optional request body (dict will be JSON-encoded).
            extra_headers: Optional additional headers to merge in.

        Returns:
            dict containing: status, url, body (parsed JSON or raw text),
            headers, and a success flag.
        """
        method = method.upper()
        if not method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            return {"success": False, "error": f"Unsupported method: {method}"}

        # Resolve relative paths
        if url.startswith("/"):
            url = f"https://www.linkedin.com{url}"

        # Extract JSESSIONID from cookies for the CSRF token
        cookies = await self._page.context.cookies()
        csrf_token = None
        for c in cookies:
            if c["name"] == "JSESSIONID":
                # LinkedIn cookie values are often enclosed in double quotes
                csrf_token = c["value"].strip('"')
                break

        # Build headers — browser session carries auth cookies automatically
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "x-restli-protocol-version": "2.0.0",
        }
        if csrf_token:
            headers["csrf-token"] = csrf_token

        if extra_headers:
            headers.update(extra_headers)

        # Encode body
        data: str | None = None
        if body is not None:
            if isinstance(body, dict):
                data = json.dumps(body)
                headers["content-type"] = "application/json"
            else:
                data = str(body)

        logger.info(f"API Executor: {method} {url}")

        try:
            # Use the browser context's request API — carries session cookies
            response = await self._page.context.request.fetch(
                url,
                method=method,
                headers=headers,
                data=data,
            )

            # Try to parse JSON body
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    response_body = await response.json()
                except Exception:
                    response_body = await response.text()
            else:
                response_body = await response.text()

            return {
                "success": response.ok,
                "status": response.status,
                "url": url,
                "method": method,
                "body": response_body,
                "headers": dict(response.headers),
            }

        except Exception as e:
            logger.error(f"API execution failed: {e}")
            return {"success": False, "error": str(e), "url": url, "method": method}

    # -------------------------------------------------------------------------
    # Endpoint Pattern Registry (Cookbook)
    # -------------------------------------------------------------------------

    def _load_registry(self) -> dict[str, Any]:
        """Load the pattern registry from disk."""
        if not self._registry_path.exists():
            return {"patterns": {}, "updated_at": None}
        try:
            return json.loads(self._registry_path.read_text(encoding="utf-8"))
        except Exception:
            return {"patterns": {}, "updated_at": None}

    def _save_registry(self, data: dict[str, Any]) -> None:
        """Persist the pattern registry to disk."""
        data["updated_at"] = datetime.now().isoformat()
        self._registry_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def save_pattern(
        self,
        name: str,
        method: str,
        url_path: str,
        body_template: dict[str, Any] | None,
        description: str,
    ) -> dict[str, Any]:
        """Save a proven endpoint pattern to the cookbook.
        If an existing pattern has the same url_path and method, it will be overwritten.

        Args:
            name:          Unique identifier (e.g. 'create_ugc_post').
            method:        HTTP verb.
            url_path:      The LinkedIn API path (e.g. '/voyager/api/ugcPosts').
            body_template: Example request body (with placeholder values).
            description:   What this endpoint does.

        Returns:
            dict confirming the saved pattern.
        """
        registry = self._load_registry()
        method_upper = method.upper()

        # Overwrite logic: if same URL path and method exists, remove it first
        keys_to_remove = []
        for existing_name, p in registry["patterns"].items():
            if p.get("url_path") == url_path and p.get("method") == method_upper:
                keys_to_remove.append(existing_name)
        
        for k in keys_to_remove:
            del registry["patterns"][k]

        registry["patterns"][name] = {
            "name": name,
            "method": method_upper,
            "url_path": url_path,
            "body_template": body_template or {},
            "description": description,
            "saved_at": datetime.now().isoformat(),
        }
        self._save_registry(registry)
        logger.info(f"Saved API pattern: '{name}'")
        return {"saved": True, "name": name, "total_patterns": len(registry["patterns"])}

    def list_patterns(self, query: str | None = None) -> list[dict[str, Any]]:
        """List all saved patterns, optionally filtered by keyword.

        Args:
            query: Search keyword to filter by name or description.

        Returns:
            List of matching pattern records.
        """
        registry = self._load_registry()
        patterns = list(registry["patterns"].values())

        if query:
            q = query.lower()
            patterns = [
                p for p in patterns
                if q in p.get("name", "").lower()
                or q in p.get("description", "").lower()
                or q in p.get("url_path", "").lower()
            ]

        return patterns

    def get_pattern(self, name: str) -> dict[str, Any] | None:
        """Retrieve a single saved pattern by name."""
        registry = self._load_registry()
        return registry["patterns"].get(name)
