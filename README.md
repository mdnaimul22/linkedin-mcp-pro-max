<p align="center">
  <h1 align="center">🌐 LinkedIn MCP Pro Max</h1>
</p>

<p align="center">
  A high-performance, autonomous <strong>Model Context Protocol (MCP)</strong> server that turns LinkedIn into an API for your AI workflows. Built with <strong>Clean Architecture</strong>, stealth browser automation, and robust self-healing APIs.
</p>

<p align="center">
  <a href="#features">
    <img src="https://img.shields.io/badge/Tools-24_Available-blue?style=for-the-badge&logo=rocket" alt="Tools">
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

## 🚀 Overview

The browser as we know it is evolving from a viewing window to an **Automated Representative**. **LinkedIn MCP Pro Max** is a Next-Gen User Agent. It acts on your behalf using your authorized session, directly passing control to LLMs via the Model Context Protocol.

✅ **Autonomous Authentication** using headless GUI injection.  
✅ **Stealth Browsing** via Patchright (bypassing normal bot detection).  
✅ **Clean Architecture** ensuring uncoupled UI scaling and 100% deterministic tooling.  
✅ **Self-Healing Endpoints** capable of automatically mapping internal LinkedIn APIs when visual UI shifts.

---

## ⚡ Quick Start

### 1. Prerequisites
Ensure you have **[uv](https://docs.astral.sh/uv/)** installed, the extremely fast Python package and project manager written in Rust.

### 2. Installation Setup
```bash
# Clone the repository
git clone <repository_url> linkedin-mcp-pro-max
cd linkedin-mcp-pro-max

# Sync dependencies and install the stealth browser
uv sync
uv run patchright install chromium
```

### 3. Configuration
Copy the configuration template and fill in your details:
```bash
cp .env.example .env
```
Ensure `.env` contains your details:
```env
LINKEDIN_USERNAME="your-email@example.com"
LINKEDIN_PASSWORD="your-secure-password"
```

### 4. Initialization (First Run)
Authenticate your session automatically securely (stores cookies locally):
```bash
uv run linkedin-mcp-pro-max --login-auto
```

### 5. Connecting with Claude Desktop (or any MCP Client)
Add the server to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "linkedin-mcp-pro-max": {
    "command": "uv",
    "args": [
      "--directory",
      "/absolute/path/to/linkedin-mcp-pro-max",
      "run",
      "linkedin-mcp-pro-max"
    ],
    "env": {}
  }
}
```

---

## 🧰 The MCP Toolkit (24 Tools)

**LinkedIn MCP Pro Max** exposes 24 specialized intelligent tools broken down by functional category.

| Category | Tool | Description |
| :--- | :--- | :--- |
| **Profile** | `get_profile` | Scrape deep profile data (experience, education, skills) |
| | `analyze_profile` | AI-driven optimization feedback on profile metrics |
| | `update_profile` | Update your specific headline and summary instantly |
| | `add_experience` | Add a new professional experience securely |
| | `edit_experience` | Edit an existing experience entry |
| | `remove_experience` | Securely remove an unwanted experience entry |
| | `manage_skills` | Add or delete skills from your profile |
| **Intel & Jobs** | `search_jobs` | Search open positions with granular filtering |
| | `get_job_details` | Scrap the full internal details of a specific job ID |
| | `get_recommended_jobs` | Fetch personalized recommendations tailored to your profile |
| | `get_company` | Extract detailed corporate metadata and structure |
| **Content** | `create_linkedin_post` | Publish professional AI-generated posts autonomously |
| | `interact_with_post` | Read, Like, or Comment on feed posts via URL |
| **Documents** | `generate_resume` | AI-generate a professional resume dynamically |
| | `tailor_resume` | Target your resume to perfectly match a specific Job ID |
| | `generate_cover_letter` | Create a highly-personalized contextualized cover letter |
| | `list_templates` | View styling templates natively supported by the system |
| **CRM** | `track_application` | Log an application directly to the internal tracking schema |
| | `list_applications` | Yield the list of all active local job tracks |
| | `update_application_status` | Update statuses (`interested`, `interviewing`, `rejected`) |
| **API Self-Healing** | `get_network_logs` | Discover hidden backend API logic directly via proxy |
| | `execute_linkedin_api` | Call raw LinkedIn internal voyager API endpoints directly |
| | `save_api_pattern` | Persist an endpoint signature uniquely to bypass DOM failures |
| | `list_api_patterns` | List community and internally saved API signature models |

---

## 🏗️ Architecture & Adding New Tools

Built strictly on **Clean Architecture**, enforcing Unidirectional Dependency rules to ensure the codebase remains maintainable, decoupled, and highly modular.

### Structure At a Glance
- `schema/` • Pydantic Domain Entities (No dependencies).
- `services/` • Business use-cases, orchestration, and logic.
- `browser/` & `api/` • Infrastructure adapters and external handlers.
- `tools/` • Interface Adapters handling strict MCP inputs/outputs.
- `app.py` • Dependency Injection Container (`AppContext`).

---

### 🔧 Adding A New Tool Properly

**Rule #1: Tools contain NO business logic.**  
Instead of putting logic in the tool, delegate it to the `Service Layer`.

#### 1. Define the Business Logic (`src/services/network.py`)
```python
from typing import Any
from helpers.exceptions import LinkedInMCPError

class NetworkService:
    def __init__(self, browser_manager):
        self._browser = browser_manager

    async def connect(self, profile_url: str) -> Any:
        if not self._browser:
            raise LinkedInMCPError("Browser unavailable.")
        # Scraping logic goes here!
        return {"status": "connected", "url": profile_url}
```

#### 2. Register Service in DI Container (`src/app.py`)
We map the service inside our core context container.
```python
from services.network import NetworkService

class AppContext:
    def __init__(self, ...):
        self.network = NetworkService(self.browser)
```

#### 3. Create the Thin Interface Tool (`src/tools/network.py`)
Validate the input, initialize the environment, and hand off to the service.
```python
import json
from fastmcp.exceptions import ToolError
from app import mcp, get_ctx

@mcp.tool()
async def connect_user(profile_url: str) -> str:
    """Connect securely to a user on LinkedIn."""
    try:
        ctx = await get_ctx()
        await ctx.initialize_browser() # Initialize environment mapping
        result = await ctx.network.connect(profile_url) # Hit the service layer
        return json.dumps(result, indent=2)
    except Exception as e:
        raise ToolError(str(e))
```

#### 4. Expose the Tool (`src/tools/__init__.py`)
Ensure your new file is loaded natively by the application during startup.
```python
from . import network
```

---

## 🛠️ CLI Reference

Additional utilities to manage the background daemon smoothly:

```bash
uv run linkedin-mcp-pro-max           # Start server
uv run linkedin-mcp-pro-max --status  # Check active stealth sessions
uv run linkedin-mcp-pro-max --logout  # Clear persistent local cache
uv run ty check                   # Type check whole project
```

---

<p align="center">
  <i>Automating your professional identity smartly, securely, and seamlessly.</i><br>
  <b><a href="https://github.com/mdnaimul22/linkedin-mcp-pro-max">Report an Issue</a></b>
</p>
