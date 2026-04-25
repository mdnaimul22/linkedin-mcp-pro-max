<p align="center">
  <h1 align="center">LinkedIn MCP Pro Max</h1>
</p>

<p align="center">
  A high-performance, autonomous <strong>Model Context Protocol (MCP)</strong> server that turns LinkedIn into an API for your AI workflows. Built with <strong>Clean Architecture</strong>, stealth browser automation, and a convention-based zero-config component registry.
</p>

<p align="center">
  <a href="#features">
    <img src="https://img.shields.io/badge/Tools-14_Unified-blue?style=for-the-badge&logo=rocket" alt="Tools">
  </a>
  <a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/badge/Package_Manager-uv-purple?style=for-the-badge&logo=python" alt="UV">
  </a>
  <a href="https://github.com/patchright/patchright">
    <img src="https://img.shields.io/badge/Automation-Patchright-green?style=for-the-badge&logo=playwright" alt="Patchright">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
  </a>
</p>

---

## Overview

The browser is evolving from a viewing window to an **Automated Representative**. **LinkedIn MCP Pro Max** is a Next-Gen User Agent. It acts on your behalf using your authorized session, directly passing control to LLMs via the Model Context Protocol.

- **Autonomous Authentication** using headless GUI injection.
- **Stealth Browsing** via Patchright (bypasses advanced bot detection).
- **Dynamic Tool Discovery** — Zero-config tool registration via `pkgutil`.
- **Unified Component Registry** — Services, actors, and scrapers auto-register at startup. `app.py` and `manager.py` never need editing.
- **Self-Healing Endpoints** — Automatically maps internal LinkedIn APIs when visual UI shifts.

---

## Quick Start

### 1. Prerequisites

Ensure you have **[uv](https://docs.astral.sh/uv/)** installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Installation & Setup

#### Method A: Automated Setup (Recommended)
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```
The script handles dependency syncing, `.env` bootstrapping, and stealth browser provisioning.

#### Method B: Manual Setup
```bash
uv sync
uv run python -m patchright install chromium
cp .env.example .env
```

### 3. Configuration

Edit `.env` with your LinkedIn credentials:
```env
LINKEDIN_USERNAME="your-email@example.com"
LINKEDIN_PASSWORD="your-secure-password"
```

### 4. First-Run Authentication
```bash
uv run linkedin-mcp-pro-max --login-auto
```

### 5. Connect to Claude Desktop (or any MCP client)

Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "linkedin-mcp-pro-max": {
    "command": "uv",
    "args": [
      "--directory",
      "/absolute/path/to/linkedin-mcp-pro-max",
      "run",
      "linkedin-mcp-pro-max"
    ]
  }
}
```

---

## The MCP Toolkit (14 Unified Tools)

| Category | Tool | Actions | Description |
| :--- | :--- | :--- | :--- |
| **Profile** | `profile` | `get`, `analyze`, `update`, `update_cover_image` | Manage deep profile data, AI analysis, and identity updates |
| | `experience` | `add`, `update`, `delete` | Manage professional experience entries |
| | `education` | `add`, `update`, `delete` | Manage education entries |
| | `skills` | `add`, `delete` | Manage skills on your profile |
| | `company` | - | Get detailed corporate metadata and insights |
| **Jobs & Intel** | `job` | `search`, `details`, `recommended`, `apply` | Discover, analyze, and apply for job postings |
| | `application` | `list`, `track`, `update` | Manage internal job application tracking |
| **Content** | `create_linkedin_post` | - | Publish AI-generated posts autonomously |
| | `interact_with_post` | `read`, `like`, `comment` | Engage with feed posts via URL |
| **Documents** | `generate_resume` | - | Generate a professional resume from your profile |
| | `tailor_resume` | - | Target your resume to match a specific Job ID |
| | `generate_cover_letter` | - | Create a personalized contextual cover letter |
| | `list_templates` | - | View all available document templates |
| **System** | `server` | `restart` | Manage the MCP server lifecycle |

---

## Architecture

Built on **Clean Architecture** with a one-way dependency rule and a **Unified Component Registry** that eliminates all manual wiring.

```
[tools/]  →  [services/]  →  [browser/actors/ + browser/scrapers/]
              ctx.my_svc        manager.my_actor / manager.my_scraper
```

### Directory Structure

```
src/
├── app.py                  # Composition root — auto-wires from registry
├── helpers/
│   └── registry.py         # Unified discovery engine (ServiceMeta, ActorMeta, ScraperMeta)
├── tools/                  # MCP tool definitions (@mcp.tool) — auto-discovered
├── services/               # Business logic layer — auto-wired via SERVICE markers
├── browser/
│   ├── actors/             # Write operations (UI interaction) — auto-registered
│   ├── scrapers/           # Read operations (data extraction) — auto-registered
│   ├── manager.py          # Orchestrator — auto-instantiates actors/scrapers
│   └── helpers/            # Low-level browser utilities (driver, sniffer, dom)
├── api/                    # LinkedIn internal API client
├── db/                     # Database repositories
├── schema/                 # Pydantic domain models
├── config/                 # Settings and environment
└── providers/              # AI provider wrappers (OpenAI, Claude)
```

### The Zero-Config Flow

At startup, `helpers/registry.py` scans `services/`, `browser/actors/`, and `browser/scrapers/` automatically:

```
discover_all()
├── services/*.py     → SERVICE = ServiceMeta(...)   → injected into AppContext
├── browser/actors/*  → ACTOR   = ActorMeta(...)     → instantiated in BrowserManager
└── browser/scrapers/ → SCRAPER = ScraperMeta(...)   → instantiated in BrowserManager
```

No manual registration. No editing `app.py` or `manager.py`.

---

## Adding New Features

> For the complete development pipeline, debugging guide, and working examples, see the **[Tool Development Guide](docs/develop_new_tool.md)**.

A full feature (scraper + service + tool) requires exactly **3 new files**. No existing file is modified.

**1. Browser Scraper** — `src/browser/scrapers/my_feature.py`
```python
from helpers.registry import ScraperMeta

class MyFeatureScraper:
    def __init__(self, page): ...
    async def scrape(self): ...

SCRAPER = ScraperMeta(attr="my_feature_scraper", cls=MyFeatureScraper)
```

**2. Service** — `src/services/my_feature.py`
```python
from helpers.registry import ServiceMeta

class MyFeatureService:
    def __init__(self, browser=None): ...
    async def do_work(self): ...

SERVICE = ServiceMeta(attr="my_feature", cls=MyFeatureService, deps=["browser"], lazy=True)
```

**3. Tool** — `src/tools/my_feature.py`
```python
from app import mcp, get_ctx

@mcp.tool()
async def my_feature_tool(param: str) -> str:
    """Description the AI reads to decide when to use this tool."""
    ctx = await get_ctx()
    await ctx.initialize_browser()
    result = await ctx.my_feature.do_work()
    return json.dumps(result)
```

`app.py`, `manager.py`, `services/__init__.py`, `tools/__init__.py` — never touched.

---

## CLI Reference

```bash
uv run linkedin-mcp-pro-max             # Start MCP server
uv run linkedin-mcp-pro-max --login-auto # Automated headless login
uv run linkedin-mcp-pro-max --login      # Interactive browser login
uv run linkedin-mcp-pro-max --status     # Check session status
uv run linkedin-mcp-pro-max --logout     # Clear local session cache
uv run ty check                          # Type-check the project
```

---

## Documentation

| Document | Description |
| :--- | :--- |
| [Tool Development Guide](docs/develop_new_tool.md) | Full pipeline: creating tools, services, actors, scrapers. Debugging guide. |
| [Services README](src/services/README.md) | Service layer conventions and dependency rules |
| [Actors README](src/browser/actors/README.md) | Actor conventions and browser interaction patterns |
| [Schema README](src/schema/README.md) | Pydantic model conventions |

---

<p align="center">
  <i>Automating your professional identity smartly, securely, and seamlessly.</i><br>
  <b><a href="https://github.com/mdnaimul22/linkedin-mcp-pro-max">Report an Issue</a></b>
</p>
