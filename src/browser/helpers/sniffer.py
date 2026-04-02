"""Network traffic sniffer for LinkedIn API reverse engineering.

Dependency Rule:
    imports FROM: standard library, patchright
    MUST NOT import: api, services, providers, tools
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from patchright.async_api import Request, Response

logger = logging.getLogger("linkedin-mcp.sniffer")


class NetworkSniffer:
    """Advanced network traffic interceptor for LinkedIn API analysis."""

    def __init__(
        self, log_dir: str = ".browser/network_logs", ttl_seconds: int = 120
    ) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.is_enabled = True  # Default to ON for autonomous behavior
        self.ttl_seconds = ttl_seconds
        self._captured_count = 0

    def enable(self, enabled: bool = True) -> None:
        """Toggle the sniffer state."""
        self.is_enabled = enabled
        status = "ENABLED" if enabled else "DISABLED"
        logger.info(f"Network Sniffer {status}")

    async def on_request(self, request: Request) -> None:
        """Handle outgoing requests with broad internal API filtering."""
        if not self.is_enabled:
            return

        # Broad filter for LinkedIn internal APIs
        is_internal = any(
            x in request.url
            for x in ["/api/", "/ajax/", "/uas/", "/voyager/", "/checkpoint/"]
        )
        is_linkedin = "linkedin.com" in request.url
        if not (is_linkedin and is_internal):
            return

        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "request",
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            }
            self._save_entry(entry)
        except Exception as exc:
            logger.debug(f"Error logging request: {exc}")

    async def on_response(self, response: Response) -> None:
        """Handle incoming responses with broad internal API filtering."""
        if not self.is_enabled:
            return

        # Broad filter matches request filtering
        is_internal = any(
            x in response.url
            for x in ["/api/", "/ajax/", "/uas/", "/voyager/", "/checkpoint/"]
        )
        is_linkedin = "linkedin.com" in response.url
        if not (is_linkedin and is_internal):
            return

        try:
            # Basic entry info
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "response",
                "status": response.status,
                "url": response.url,
                "headers": dict(response.headers),
                "body": None,
            }

            # Try to parse response body if it's JSON
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    entry["body"] = await response.json()
                except Exception:
                    # Body might be binary or malformed JSON
                    pass

            self._save_entry(entry)
        except Exception as exc:
            logger.debug(f"Error logging response: {exc}")

    def _cleanup_old_logs(self) -> int:
        """Automatic cleanup of logs older than ttl_seconds."""
        now = datetime.now().timestamp()
        count = 0
        try:
            for f in self.log_dir.glob("*.json"):
                if now - f.stat().st_mtime > self.ttl_seconds:
                    f.unlink()
                    count += 1
            if count > 0:
                logger.debug(f"Auto-cleaned {count} old network logs")
        except Exception as exc:
            logger.error(f"Failed to auto-cleanup sniffer logs: {exc}")
        return count

    def log_external_call(
        self,
        type: str,  # "request" or "response"
        url: str,
        method: str | None = None,
        status: int | None = None,
        headers: dict[str, str] | None = None,
        body: Any = None,
    ) -> None:
        """
        Manually log an external network call (e.g. from an API client).
        This allows non-browser components to share the same sniffer discovery logs.
        """
        if not self.is_enabled:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": type,
            "url": url,
            "headers": dict(headers) if headers else {},
        }

        if type == "request":
            entry["method"] = method or "GET"
            entry["post_data"] = body
        else:
            entry["status"] = status or 200
            entry["body"] = body

        self._save_entry(entry)

    def _save_entry(self, entry: dict[str, Any]) -> None:
        """Persist a captured entry to a JSON file and trigger cleanup."""
        # Cleanup before saving to ensure we stay lean
        self._cleanup_old_logs()

        self._captured_count += 1
        # Use microsecond precision for filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_{entry['type']}.json"
        filepath = self.log_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save sniffer entry: {exc}")

    def clear_logs(self) -> int:
        """Remove all captured log files."""
        count = 0
        for f in self.log_dir.glob("*.json"):
            f.unlink()
            count += 1
        self._captured_count = 0
        logger.info(f"Cleared {count} network logs")
        return count

    def get_recent_logs(
        self,
        limit: int = 10,
        query: str | None = None,
        method: str | None = None,
        status: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent logs with advanced filtering and deep search."""
        self._cleanup_old_logs()

        files = sorted(
            self.log_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        )
        logs = []

        for f in files:
            if len(logs) >= limit:
                break

            try:
                with open(f, "r", encoding="utf-8") as log_file:
                    entry = json.load(log_file)

                    # Apply Filters

                    # 1. Method Filter
                    if method and entry.get("method", "").upper() != method.upper():
                        continue

                    # 2. Status Filter
                    if status and entry.get("status") != status:
                        continue

                    # 3. Deep Search (Query)
                    if query:
                        query_lower = query.lower()
                        # Search in URL
                        url_match = query_lower in entry.get("url", "").lower()
                        # Search in Post Data
                        post_match = (
                            query_lower in str(entry.get("post_data", "")).lower()
                        )
                        # Search in Response Body
                        body_match = (
                            query_lower in json.dumps(entry.get("body", "")).lower()
                        )

                        if not (url_match or post_match or body_match):
                            continue

                    logs.append(entry)
            except Exception:
                continue
        return logs
