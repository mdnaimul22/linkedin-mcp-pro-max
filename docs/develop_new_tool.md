# Tool Development Guide — LinkedIn MCP Pro Max

This document is the **single source of truth** for developing, debugging, and shipping new tools on the LinkedIn MCP Pro Max platform. It reflects the current **Zero-Config, Convention-Based Architecture**.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Development Decision Tree](#2-development-decision-tree)
3. [Pipeline: Adding a New Tool (End-to-End)](#3-pipeline-adding-a-new-tool-end-to-end)
   - [Step 1 — Browser Layer (Scraper or Actor)](#step-1--browser-layer-scraper-or-actor)
   - [Step 2 — Service Layer](#step-2--service-layer)
   - [Step 3 — Tool Layer](#step-3--tool-layer)
4. [The Zero-Config Registry Contract](#4-the-zero-config-registry-contract)
5. [Full Working Example: `send_connection_request`](#5-full-working-example-send_connection_request)
6. [Debugging Guide](#6-debugging-guide)
7. [Checklist](#7-checklist-before-every-pr)

---

## 1. Architecture Overview

The system follows a strict **layered architecture** with a one-way dependency rule:

```
[Tool Layer]  →  [Service Layer]  →  [Browser Layer (Actor/Scraper)]
     ↓                  ↓                        ↓
  tools/*.py        services/*.py       browser/actors/*.py
  @mcp.tool()       ctx.my_service      browser/scrapers/*.py
```

```
Startup Flow
────────────
1. helpers/registry.py   → discover_all() scans services/, actors/, scrapers/
2. app.py AppContext      → _wire_services(lazy=False) injects eager services
3. Tools call            → ctx.initialize_browser() triggers lazy services + actors/scrapers
4. MCP Server            → @mcp.tool() functions exposed to the AI client
```

**Golden Rule:** A tool function should contain almost **no logic**. It calls a service. The service calls an actor or scraper. Each layer does exactly one thing.

---

## 2. Development Decision Tree

Before writing a single line of code, decide where your feature belongs:

```
What does my feature do?
│
├── Clicks a button / types text / navigates a page?
│     └── → browser/actors/<name>.py  (Actor)
│
├── Reads / extracts data from a LinkedIn page?
│     └── → browser/scrapers/<name>.py  (Scraper)
│
├── Calls the LinkedIn internal API directly (no browser UI)?
│     └── → api/linkedin.py  (API Client method)
│
├── Combines multiple sources (DB + API + Browser + AI)?
│     └── → services/<name>.py  (Service)
│
└── Exposes the feature to the AI / MCP client?
      └── → tools/<name>.py  (Tool)
```

> **Rule:** Never put browser logic in a service. Never call `ctx.db` from a tool directly. Every layer must stay within its boundary.

---

## 3. Pipeline: Adding a New Tool (End-to-End)

### Step 1 — Browser Layer (Scraper or Actor)

**File location:**
- Read operations → `src/browser/scrapers/<feature>.py`
- Write operations → `src/browser/actors/<feature>.py`

**Convention (MANDATORY):**
Every scraper/actor class:
1. Accepts only `page: Page` in its constructor.
2. Declares a `SCRAPER` or `ACTOR` convention marker at the bottom.

```python
# src/browser/scrapers/events.py
from __future__ import annotations
import logging
from typing import Any
from patchright.async_api import Page

from helpers.registry import ScraperMeta  # import the registry

logger = logging.getLogger("linkedin-mcp.scrapers.events")


class EventsScraper:
    """Scrapes LinkedIn event listings."""

    def __init__(self, page: Page) -> None:
        self._page = page

    async def scrape_events(self, keywords: str) -> list[dict[str, Any]]:
        """Navigate to events search and extract event data."""
        url = f"https://www.linkedin.com/search/results/events/?keywords={keywords}"
        await self._page.goto(url, wait_until="domcontentloaded")
        # ... extraction logic ...
        return []


# ── Registry Convention ───────────────────────────────────────────────────────
# This ONE line is all that's needed. No other file needs to be touched.
SCRAPER = ScraperMeta(attr="events_scraper", cls=EventsScraper)
```

Access in services: `browser_manager.events_scraper.scrape_events(...)`

> `app.py` এবং `browser/manager.py` — এই দুটোতে **কখনো হাত দেবেন না।**

---

### Step 2 — Service Layer

**File location:** `src/services/<feature>.py`

A service orchestrates: it calls scrapers/actors, applies business logic, interacts with DB, calls AI.

**Convention (MANDATORY):**
Every service declares a `SERVICE` metadata marker at the bottom.

```python
# src/services/events.py
from __future__ import annotations
import logging
from typing import Any

from browser.manager import BrowserManager
from helpers.registry import ServiceMeta

logger = logging.getLogger("linkedin-mcp.services.events")


class EventsService:
    """Manages LinkedIn events discovery and scraping."""

    def __init__(self, browser: BrowserManager | None = None) -> None:
        self._browser = browser

    async def find_events(self, keywords: str) -> list[dict[str, Any]]:
        if not self._browser:
            raise RuntimeError("Browser required for events scraping.")
        return await self._browser.events_scraper.scrape_events(keywords)


# ── Registry Convention ───────────────────────────────────────────────────────
SERVICE = ServiceMeta(
    attr="events",          # ctx.events will be the EventsService instance
    cls=EventsService,
    deps=["browser"],       # AppContext.browser will be passed as kwarg
    lazy=True,              # True = needs browser; wired after initialize_browser()
)
```

**`deps` ← list of AppContext attribute names to inject:**

| dep string | What gets injected |
|---|---|
| `"client"` | `LinkedInClient` |
| `"db"` | `DatabaseService` |
| `"browser"` | `BrowserManager` |
| `"ai"` | `BaseProvider` (Claude / OpenAI) |
| `"cache"` | `JSONCache` |
| `"sessions"` | `SessionManager` |

**Factory pattern (for complex dependencies):**

Use `factory` instead of `deps` when constructor args don't map 1:1 to AppContext attrs:

```python
SERVICE = ServiceMeta(
    attr="resume_gen",
    cls=ResumeGeneratorService,
    lazy=True,
    factory=lambda ctx: ResumeGeneratorService(
        ctx.profiles, ctx.jobs, ctx.ai,
        ctx.template_manager,
        ctx.settings.data_dir / "resumes",
    ),
)
```

> `services/__init__.py` এবং `app.py` — এই দুটোতে **কখনো হাত দেবেন না।**

---

### Step 3 — Tool Layer

**File location:** `src/tools/<feature>.py`

Tool functions are the public API exposed to the MCP client (Claude, Cursor, etc.). They must be:
- Thin (no business logic)
- Descriptive (the docstring is what the AI reads to decide when to call this tool)
- Typed (all parameters and return type declared)

```python
# src/tools/events.py
from __future__ import annotations
import json
import logging

from app import get_ctx, mcp

logger = logging.getLogger("linkedin-mcp.tools.events")


@mcp.tool()
async def search_linkedin_events(keywords: str, max_results: int = 10) -> str:
    """
    Search for LinkedIn events matching the given keywords.

    Use this when the user wants to discover professional events, webinars,
    conferences, or networking meetups on LinkedIn.

    Args:
        keywords:    Topics or event name to search for.
        max_results: Maximum number of events to return (default 10).

    Returns:
        JSON string with a list of matching events.
    """
    ctx = await get_ctx()
    await ctx.initialize_browser()          # starts browser + wires lazy services

    events = await ctx.events.find_events(keywords)
    return json.dumps({"events": events[:max_results], "total": len(events)})
```

That's it. The `@mcp.tool()` decorator and the file being in `src/tools/` is all that's needed — **`tools/__init__.py` auto-discovers it at startup.**

---

## 4. The Zero-Config Registry Contract

The entire system is powered by `src/helpers/registry.py`. Here is what happens at boot:

```
startup (cli.py)
    │
    ├── discover_all()                ← scans services/, actors/, scrapers/
    │     ├─ finds SERVICE markers   → adds to _SERVICE_REGISTRY
    │     ├─ finds ACTOR markers     → adds to _ACTOR_REGISTRY
    │     └─ finds SCRAPER markers   → adds to _SCRAPER_REGISTRY
    │
    ├── AppContext.__post_init__()
    │     └─ _wire_services(lazy=False)  → instantiates all eager services
    │
    └── ctx.initialize_browser()  [called by any browser-dependent tool]
          ├─ BrowserManager.start()
          │     ├─ loop _ACTOR_REGISTRY   → actor = cls(page)
          │     └─ loop _SCRAPER_REGISTRY → scraper = cls(page)
          └─ _wire_services(lazy=True)    → instantiates lazy services
```

**Summary — Files you edit per feature:**

| What you add | Files to create/edit |
|---|---|
| New browser capability | `browser/scrapers/<name>.py` or `browser/actors/<name>.py` |
| New business logic | `services/<name>.py` |
| New tool for MCP client | `tools/<name>.py` |
| New DB repository | `db/repositories/<name>.py` |
| New Pydantic schema | `schema/<name>.py` |

**Files you NEVER edit:**
- `app.py` — auto-wires services from registry
- `browser/manager.py` — auto-instantiates actors/scrapers from registry
- `services/__init__.py` — no manual imports
- `tools/__init__.py` — auto-discovers tool files

---

## 5. Full Working Example: `send_connection_request`

This example implements an end-to-end feature from scratch.

### `browser/actors/networking.py`

```python
from __future__ import annotations
import logging
from patchright.async_api import Page
from helpers.registry import ActorMeta

logger = logging.getLogger("linkedin-mcp.actors.networking")


class NetworkingActor:
    """Handles LinkedIn connection and follow actions."""

    def __init__(self, page: Page) -> None:
        self._page = page

    async def send_connection_request(
        self, profile_url: str, message: str | None = None
    ) -> dict:
        """Navigate to a profile and click Connect."""
        await self._page.goto(profile_url, wait_until="domcontentloaded")

        connect_btn = self._page.locator("button:has-text('Connect')")
        if not await connect_btn.count():
            return {"status": "error", "reason": "Connect button not found"}

        await connect_btn.first.click()

        if message:
            add_note_btn = self._page.locator("button:has-text('Add a note')")
            if await add_note_btn.count():
                await add_note_btn.click()
                await self._page.fill("textarea[name='message']", message)

        send_btn = self._page.locator("button:has-text('Send')")
        if await send_btn.count():
            await send_btn.click()
            return {"status": "sent"}

        return {"status": "error", "reason": "Send button not found"}


ACTOR = ActorMeta(attr="networking_actor", cls=NetworkingActor)
```

### `services/networking.py`

```python
from __future__ import annotations
import logging
from typing import Any
from browser.manager import BrowserManager
from helpers.registry import ServiceMeta

logger = logging.getLogger("linkedin-mcp.services.networking")


class NetworkingService:
    """Manages LinkedIn connection and networking actions."""

    def __init__(self, browser: BrowserManager | None = None) -> None:
        self._browser = browser

    async def send_connection_request(
        self, profile_url: str, message: str | None = None
    ) -> dict[str, Any]:
        if not self._browser:
            raise RuntimeError("Browser not initialized.")
        return await self._browser.networking_actor.send_connection_request(
            profile_url, message
        )


SERVICE = ServiceMeta(
    attr="networking",
    cls=NetworkingService,
    deps=["browser"],
    lazy=True,
)
```

### `tools/networking.py`

```python
from __future__ import annotations
import json
import logging
from typing import Optional
from app import get_ctx, mcp

logger = logging.getLogger("linkedin-mcp.tools.networking")


@mcp.tool()
async def send_connection_request(
    profile_url: str,
    message: Optional[str] = None,
) -> str:
    """
    Send a LinkedIn connection request to a profile.

    Use this when the user wants to connect with another LinkedIn member.
    Optionally include a personalized message with the request.

    Args:
        profile_url: Full LinkedIn profile URL (e.g., https://linkedin.com/in/username).
        message:     Optional personalized message to attach (max 300 chars).

    Returns:
        JSON with status: "sent" on success, "error" with reason on failure.
    """
    ctx = await get_ctx()
    await ctx.initialize_browser()
    result = await ctx.networking.send_connection_request(profile_url, message)
    return json.dumps(result)
```

**Result:** 3 new files created. 0 existing files modified. Feature is live.

---

## 6. Debugging Guide

### Tool not appearing in MCP client?

Check that:
1. File is in `src/tools/` (not a subdirectory).
2. Function has `@mcp.tool()` decorator.
3. Server was restarted after adding the file.

Verify discovery:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
import tools  # triggers discovery
from app import mcp
print([t.name for t in mcp._tool_manager.list_tools()])
"
```

### Service not wiring (AttributeError on `ctx.my_service`)?

Check the `SERVICE` marker in your service file:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from helpers.registry import discover_all, get_services
discover_all()
for s in get_services():
    print(s.attr, '->', s.cls.__name__, '| lazy:', s.lazy)
"
```

Common mistakes:
- `SERVICE` variable name is misspelled (must be exactly `SERVICE`).
- The file is in `services/helpers/` — the scanner skips that directory.
- A constructor kwarg in `deps` doesn't match the actual `__init__` parameter name → use `factory` instead.

### Actor/Scraper not available on `browser_manager`?

Check the `ACTOR`/`SCRAPER` marker:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from helpers.registry import discover_all, get_actors, get_scrapers
discover_all()
for a in get_actors():
    print('ACTOR  ', a.attr, '->', a.cls.__name__)
for s in get_scrapers():
    print('SCRAPER', s.attr, '->', s.cls.__name__)
"
```

Common mistakes:
- Class constructor takes more than just `page` — actors/scrapers **must** accept only `page: Page`.
- The file is in `browser/helpers/` — the scanner skips that directory.
- `ACTOR` / `SCRAPER` variable name is wrong.

### Browser action is flaky or failing?

1. Check `browser/helpers/dom.py` for reusable wait/interact utilities.
2. Add `await page.wait_for_timeout(500)` between actions if LinkedIn rate-limits clicks.
3. Use `NetworkSniffer` to inspect what LinkedIn's internal API sends:
   ```python
   ctx.browser.toggle_sniffing(True)
   # ... run the action ...
   logs = ctx.browser.sniffer.get_recent_logs(query="voyager")
   ```
4. Consider using the API executor instead of DOM manipulation for more stable results.

### Checking full system health:

```bash
uv run python /tmp/smoke_test.py
```

---

## 7. Checklist Before Every PR

- [ ] **Browser layer** — class accepts only `page: Page`; `ACTOR` or `SCRAPER` marker at bottom.
- [ ] **Service layer** — `SERVICE` marker; `deps` kwargs match constructor param names exactly, OR `factory` is used.
- [ ] **Lazy flag** — `lazy=True` if the service uses `browser`, `browser_manager`, or any lazy service as a dep.
- [ ] **Tool docstring** — accurately describes WHEN the AI should call this tool (not just what it does).
- [ ] **Return type** — tool returns `str` (JSON string), not a raw dict or Pydantic model.
- [ ] **Error handling** — tool catches exceptions and returns a JSON error object, never raises.
- [ ] **Discovery verified** — ran the registry check and confirmed your component appears.
- [ ] **No forbidden imports** — no `from app import AppContext` inside services; no `ctx.db` calls inside tools.
