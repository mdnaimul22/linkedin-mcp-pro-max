"""Playwright trace capture helper — private to browser/ module only.

Dependency Rule:
  imports FROM: standard library, config, helpers (global)
  MUST NOT import: api, session, providers, services, tools
"""

from __future__ import annotations

import itertools
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from config.settings import get_settings
from helpers import slugify_fragment

logger = logging.getLogger("linkedin-mcp.trace")

_TRACE_COUNTER = itertools.count(1)
_TRACE_DIR: Path | None = None
_TRACE_KEEP = False
_EXPLICIT_TRACE_DIR = False


def _trace_root(auth_root: Path) -> Path:
    """Return the root directory for trace runs."""
    root = auth_root / "trace-runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def trace_enabled() -> bool:
    """Check if trace capture is enabled globally."""
    settings = get_settings()
    return bool(settings.debug_trace_dir) or settings.trace_mode != "off"


def get_trace_dir(auth_root: Path) -> Path | None:
    """Return the current active trace directory, creating one if needed."""
    global _TRACE_DIR, _EXPLICIT_TRACE_DIR

    settings = get_settings()
    if settings.debug_trace_dir:
        _EXPLICIT_TRACE_DIR = True
        if _TRACE_DIR is None:
            _TRACE_DIR = settings.debug_trace_dir.expanduser().resolve()
        return _TRACE_DIR

    if settings.trace_mode == "off":
        return None

    if _TRACE_DIR is None:
        _TRACE_DIR = Path(
            tempfile.mkdtemp(prefix="run-", dir=_trace_root(auth_root))
        ).resolve()
    return _TRACE_DIR


def mark_trace_for_retention(auth_root: Path) -> Path | None:
    """Signal that the current trace should be preserved even on success."""
    global _TRACE_KEEP
    trace_dir = get_trace_dir(auth_root)
    if trace_dir is not None:
        trace_dir.mkdir(parents=True, exist_ok=True)
        _TRACE_KEEP = True
    return trace_dir


def should_keep_traces() -> bool:
    """Check if traces should be kept based on mode or explicit retention."""
    settings = get_settings()
    return _EXPLICIT_TRACE_DIR or _TRACE_KEEP or settings.trace_mode == "always"


def cleanup_trace_dir() -> None:
    """Remove the temporary trace directory if not marked for retention."""
    global _TRACE_DIR, _TRACE_KEEP, _EXPLICIT_TRACE_DIR

    trace_dir = _TRACE_DIR
    if trace_dir is None or should_keep_traces():
        return
    try:
        shutil.rmtree(trace_dir)
        _TRACE_DIR = None
    except OSError as exc:
        logger.debug("Could not cleanup trace dir %s: %s", trace_dir, exc)

    _TRACE_KEEP = False
    _EXPLICIT_TRACE_DIR = False


def reset_trace_state_for_testing() -> None:
    """Reset global trace state (for test isolation only)."""
    global _TRACE_COUNTER, _TRACE_DIR, _TRACE_KEEP, _EXPLICIT_TRACE_DIR
    _TRACE_COUNTER = itertools.count(1)
    _TRACE_DIR = None
    _TRACE_KEEP = False
    _EXPLICIT_TRACE_DIR = False


async def record_page_trace(
    page: Any, step: str, auth_root: Path, *, extra: dict[str, Any] | None = None
) -> None:
    """Persist a screenshot and basic page state when trace capture is enabled."""
    trace_dir = get_trace_dir(auth_root)
    if trace_dir is None:
        return

    trace_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = trace_dir / "screens"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    step_id = next(_TRACE_COUNTER)
    slug = slugify_fragment(step) or "step"

    try:
        title = await page.title()
    except Exception as exc:
        title = f"<error: {exc}>"

    try:
        body_text = await page.evaluate("() => document.body?.innerText || ''")
    except Exception as exc:
        body_text = f"<error: {exc}>"

    if not isinstance(body_text, str):
        body_text = ""

    try:
        remember_me = (await page.locator("#rememberme-div").count()) > 0
    except Exception:
        remember_me = False

    try:
        cookies = await page.context.cookies()
    except Exception:
        cookies = []

    linkedin_cookie_names = sorted(
        {
            cookie["name"]
            for cookie in cookies
            if "linkedin.com" in cookie.get("domain", "")
        }
    )

    screenshot_path = screenshot_dir / f"{step_id:03d}-{slug}.png"
    screenshot: str | None = None
    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
        screenshot = str(screenshot_path)
    except Exception as exc:
        screenshot = f"<error: {exc}>"

    payload = {
        "step_id": step_id,
        "step": step,
        "url": getattr(page, "url", ""),
        "title": title,
        "remember_me": remember_me,
        "body_length": len(body_text),
        "body_marker": " ".join(body_text.split())[:200],
        "linkedin_cookie_names": linkedin_cookie_names,
        "screenshot": screenshot,
        "extra": extra or {},
    }

    with (trace_dir / "trace.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
