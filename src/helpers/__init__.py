"""Global shared utility helpers.

These utilities are used by multiple top-level modules.
Rule: Only imports from standard library, config, or schema — NEVER from api, browser,
session, providers, services, or tools.
"""

import os
import re
import tempfile
from datetime import UTC, datetime
from typing import Any
from config import Settings, setup_logger, ensure_dir, exists, delete

logger = setup_logger(Settings.LOG_DIR / "helper.log", name="linkedin-mcp.helpers")


def sanitize_filename(value: str, max_length: int = 200) -> str:
    """Sanitize a string for safe use as a filesystem path component."""
    return re.sub(r"[^\w\-]", "_", value)[:max_length]


def slugify_fragment(value: str) -> str:
    """Return a lowercase URL/file-safe slug from an arbitrary string."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def utcnow_iso() -> str:
    """Return the current UTC timestamp in compact ISO-8601 form (e.g. 2024-01-15T10:30:00Z)."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def secure_mkdir(path: Any, mode: int = 0o700) -> None:
    """Create a directory tree with restrictive (owner-only) permissions."""
    # Note: ensure_dir doesn't take mode, so we use it to ensure it exists
    # but might need to set mode manually if strict requirement
    ensure_dir(str(path))
    try:
        os.chmod(str(path), mode)
    except OSError as e:
        logger.debug(f"Failed to set directory permissions on {path}: {e}")
        pass


def secure_write_text(path: Any, content: str, mode: int = 0o600) -> None:
    """Atomically write *content* to *path* with owner-only file permissions.

    Uses a temp file + os.replace() to avoid partial writes.
    """
    parent = str(path.parent)
    ensure_dir(parent)
    
    fd_int, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd_int, "w") as f:
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, str(path))
    except Exception:
        if exists(tmp):
            delete(tmp)
        raise


def is_interactive_environment() -> bool:
    """Return True if we appear to be running in an interactive terminal."""
    try:
        return os.isatty(0) and os.isatty(1)
    except (OSError, AttributeError) as e:
        logger.debug(f"Failed to detect if environment is interactive: {e}")
        return False
