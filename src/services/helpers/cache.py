"""File-based JSON cache with TTL support.

Private helper for the services/ module — used by jobs and profile caching.

Dependency Rule:
  imports FROM: standard library, config, helpers(global)
  MUST NOT import: api, browser, session, providers, tools
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from config import get_settings
from helpers import sanitize_filename

logger = logging.getLogger("linkedin-mcp.cache")


class JSONCache:
    """JSON file-based cache with TTL support."""

    def __init__(
        self, cache_dir: Path | None = None, ttl_hours: int | None = None
    ) -> None:
        settings = get_settings()
        self._cache_dir = cache_dir or settings.data_dir / "cache"
        self._ttl_seconds = (ttl_hours or settings.cache_ttl_hours) * 3600

    def _get_path(self, namespace: str, key: str) -> Path:
        safe_ns = sanitize_filename(namespace)
        safe_key = sanitize_filename(key)
        result = self._cache_dir / safe_ns / f"{safe_key}.json"

        # Security: ensure path stays within cache directory
        try:
            if not result.resolve().is_relative_to(self._cache_dir.resolve()):
                raise ValueError(
                    f"Invalid cache path: namespace={namespace}, key={key}"
                )
        except (OSError, ValueError):
            pass
        return result

    async def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Return cached item or None if missing or expired."""
        path = self._get_path(namespace, key)

        def _read() -> dict[str, Any] | None:
            if not path.exists():
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if time.time() - cached.get("_cached_at", 0) > self._ttl_seconds:
                    path.unlink(missing_ok=True)
                    return None
                return cached.get("data")  # type: ignore[no-any-return]
            except (json.JSONDecodeError, KeyError):
                path.unlink(missing_ok=True)
                return None

        return await asyncio.to_thread(_read)

    async def set(self, namespace: str, key: str, data: dict[str, Any]) -> None:
        """Store item in cache."""
        path = self._get_path(namespace, key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {"_cached_at": time.time(), "data": data}, f, indent=2, default=str
                )

        await asyncio.to_thread(_write)
        logger.debug("Cached %s/%s", namespace, key)

    async def delete(self, namespace: str, key: str) -> None:
        """Remove cached item."""
        path = self._get_path(namespace, key)

        def _unlink() -> None:
            path.unlink(missing_ok=True)

        await asyncio.to_thread(_unlink)

    async def clear(self, namespace: str | None = None) -> None:
        """Clear all cache or just a specific namespace."""

        def _clear() -> None:
            if namespace:
                ns_dir = self._cache_dir / sanitize_filename(namespace)
                if ns_dir.exists():
                    for f in ns_dir.glob("*.json"):
                        f.unlink(missing_ok=True)
            elif self._cache_dir.exists():
                for ns_dir in self._cache_dir.iterdir():
                    if ns_dir.is_dir():
                        for f in ns_dir.glob("*.json"):
                            f.unlink(missing_ok=True)

        await asyncio.to_thread(_clear)
