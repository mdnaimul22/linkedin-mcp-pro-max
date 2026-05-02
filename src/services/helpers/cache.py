import asyncio
import json
import time
from typing import Any

from config import Settings, setup_logger, ensure_dir, exists, delete
from helpers import sanitize_filename

logger = setup_logger(Settings.LOG_DIR / "cache.log", name="linkedin-mcp.cache")


class JSONCache:
    """JSON file-based cache with TTL support and L1 in-memory dictionary."""

    def __init__(
        self, cache_dir: Any | None = None, ttl_hours: int | None = None
    ) -> None:
        self._cache_dir = cache_dir or Settings.DATA_DIR / "cache"
        self._ttl_seconds = (ttl_hours or Settings.cache_ttl_hours) * 3600
        self._l1: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

    def _get_path(self, namespace: str, key: str) -> Any:
        safe_ns = sanitize_filename(namespace)
        safe_key = sanitize_filename(key)
        result = self._cache_dir / safe_ns / f"{safe_key}.json"

        # Security: ensure path stays within cache directory
        try:
            if not result.resolve().is_relative_to(self._cache_dir.resolve()):
                raise ValueError(
                    f"Invalid cache path: namespace={namespace}, key={key}"
                )
        except (OSError, ValueError) as e:
            logger.debug(f"Cache path validation failed: {e}")
        return result

    async def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Return cached item or None if missing or expired."""
        now = time.time()
        l1_key = (namespace, key)
        
        # 1. Check L1 in-memory cache
        if l1_key in self._l1:
            cached_at, data = self._l1[l1_key]
            if now - cached_at <= self._ttl_seconds:
                return data
            else:
                del self._l1[l1_key]

        path = self._get_path(namespace, key)

        # 2. Check L2 file cache
        def _read() -> tuple[float, dict[str, Any]] | None:
            if not path.exists():
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                cached_at = cached.get("_cached_at", 0)
                if time.time() - cached_at > self._ttl_seconds:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError as e:
                        logger.debug(f"Failed to delete expired cache file {path}: {e}")
                    return None
                return cached_at, cached.get("data")
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.debug(f"Cache read failed for {path}: {e}")
                try:
                    path.unlink(missing_ok=True)
                except OSError as e2:
                    logger.debug(f"Failed to delete corrupted cache file {path}: {e2}")
                return None

        result = await asyncio.to_thread(_read)
        if result:
            cached_at, data = result
            self._l1[l1_key] = (cached_at, data)  # populate L1
            return data
            
        return None

    async def set(self, namespace: str, key: str, data: dict[str, Any]) -> None:
        """Store item in cache."""
        now = time.time()
        l1_key = (namespace, key)
        
        # 1. Write to L1
        self._l1[l1_key] = (now, data)
        
        path = self._get_path(namespace, key)

        # 2. Write to L2
        def _write() -> None:
            ensure_dir(str(path.parent))
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {"_cached_at": now, "data": data}, f, indent=2, default=str
                )

        await asyncio.to_thread(_write)
        logger.debug(f"Cached {namespace}/{key}")

    async def delete_item(self, namespace: str, key: str) -> None:
        """Remove cached item."""
        l1_key = (namespace, key)
        self._l1.pop(l1_key, None)
        
        path = self._get_path(namespace, key)

        def _unlink() -> None:
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                logger.debug(f"Failed to delete cache file {path}: {e}")

        await asyncio.to_thread(_unlink)

    async def clear(self, namespace: str | None = None) -> None:
        """Clear all cache or just a specific namespace."""
        if namespace:
            self._l1 = {k: v for k, v in self._l1.items() if k[0] != namespace}
        else:
            self._l1.clear()

        def _clear() -> None:
            if namespace:
                ns_dir = self._cache_dir / sanitize_filename(namespace)
                if ns_dir.exists():
                    for f in ns_dir.glob("*.json"):
                        try:
                            f.unlink(missing_ok=True)
                        except OSError as e:
                            logger.debug(f"Failed to delete cache file {f}: {e}")
            elif self._cache_dir.exists():
                for ns_dir in self._cache_dir.iterdir():
                    if ns_dir.is_dir():
                        for f in ns_dir.glob("*.json"):
                            try:
                                f.unlink(missing_ok=True)
                            except OSError as e:
                                logger.debug(f"Failed to delete cache file {f}: {e}")

        await asyncio.to_thread(_clear)
