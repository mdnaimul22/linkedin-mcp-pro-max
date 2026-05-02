"""
LinkedIn MCP Pro Max - Composition Root
---------------------------------------
This module serves as the entry point and composition root for the MCP server.
It orchestrates the initialization of shared state, browser automation, 
and dynamic service wiring.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncIterator, Optional

from fastmcp import FastMCP

from config import Settings, setup_logger
from browser.manager import Manager, create_browser
from browser.session import Session
from browser.helpers.executor import ApiExecutor
from providers.linkedin import LinkedInClient
from providers.factory import create_ai_provider, create_image_provider

# We keep JSONCache in services.helpers for now as per original structure,
# but AppContext (the Composition Root) is allowed to import it.
from services.helpers import JSONCache
from services.auth import AuthResolver
from helpers.registry import discover_all, get_services

if TYPE_CHECKING:
    from providers import BaseProvider
    from providers.image import ImageProvider
    
    # Type hints for dynamic services (wired at runtime)
    from services.profile import ProfileService
    from services.jobs import JobSearchService
    from services.tracker import JobTrackerService
    from services.resume import ResumeGenerator
    from services.cover_letter import CoverLetterGeneratorService
    from services.profile_analyzer import ProfileAnalyzerService

logger = setup_logger(Settings.LOG_DIR / "app.log", name="linkedin-mcp.app")

@dataclass
class AppContext:
    """
    Unified application context that manages shared state and service wiring.
    Acts as the 'brain' of the MCP server, connecting all layers.
    """
    settings: Settings
    sessions: Session
    client: LinkedInClient
    
    # Infrastructure
    lock: asyncio.Lock = field(init=False)
    cache: JSONCache = field(init=False)
    ai: Optional[BaseProvider] = field(init=False)
    image_provider: Optional[ImageProvider] = field(init=False)
    
    # Browser components
    browser: Optional[Manager] = field(default=None)
    api_executor: Optional[ApiExecutor] = field(default=None)
    
    # Dynamic Service Hints (Satisfies static analysis)
    profiles: ProfileService = field(init=False)
    jobs: JobSearchService = field(init=False)
    tracker: JobTrackerService = field(init=False)
    resume_gen: ResumeGenerator = field(init=False)
    cover_letter_gen: CoverLetterGeneratorService = field(init=False)
    profile_analyzer: ProfileAnalyzerService = field(init=False)

    def __post_init__(self) -> None:
        self.lock = asyncio.Lock()
        self.cache = JSONCache(self.settings.DATA_DIR / "cache")
        
        # Initialize providers via factory
        self.ai = create_ai_provider(self.settings)
        self.image_provider = create_image_provider(self.settings)
        
        # Phase 1: Wire non-browser dependent services
        self._wire_services(lazy=False)

    def _wire_services(self, lazy: bool) -> None:
        """Wire services from the registry using multi-pass resolution."""
        pending = [m for m in get_services() if m.lazy == lazy]
        max_passes = len(pending) + 1

        for pass_num in range(1, max_passes + 1):
            still_pending = []
            for meta in pending:
                try:
                    if meta.factory:
                        instance = meta.factory(self)
                    else:
                        kwargs = {dep: getattr(self, dep, None) for dep in meta.deps}
                        instance = meta.cls(**kwargs)
                    setattr(self, meta.attr, instance)
                    logger.debug(f"Wired service: {meta.attr} -> {meta.cls.__name__} (pass {pass_num})")
                except Exception as exc:
                    still_pending.append((meta, exc))

            if not still_pending:
                break
            if len(still_pending) == len(pending):
                failed = [(m.attr, m.cls.__name__, str(exc)) for m, exc in still_pending]
                details = "; ".join(f"{attr} ({cls}): {err}" for attr, cls, err in failed)
                raise RuntimeError(f"Service wiring deadlock in pass {pass_num}: {details}")
            pending = [m for m, _ in still_pending]

    async def initialize_browser(self) -> None:
        """Provision the stealth browser and wire dependent services."""
        # Check if browser exists and is still connected/active
        try:
            if self.browser and getattr(self.browser, "_page", None) and not self.browser._page.is_closed():
                return
        except Exception:
            pass

        self.browser = await create_browser(
            session_manager=self.sessions,
            headless=self.settings.headless,
            cdp_url=self.settings.cdp_url,
            viewport_width=self.settings.viewport_width,
            viewport_height=self.settings.viewport_height,
            slow_mo=self.settings.slow_mo,
        )

        # Phase 2: Wire browser-dependent services
        self._wire_services(lazy=True)

        self.api_executor = ApiExecutor(
            page=self.browser.page,
            registry_path=self.settings.DATA_DIR / "api_cookbook.json",
        )
        self.browser.set_api_executor(self.api_executor)
        logger.info("Browser initialized - all services wired.")

# --- Singleton Management ---

_context: AppContext | None = None

async def get_ctx() -> AppContext:
    """Retrieve or lazily initialize the global AppContext singleton."""
    global _context
    if not _context:
        settings = Settings
        sessions = Session(settings)
        client = LinkedInClient(settings)
        _context = AppContext(settings, sessions, client)
    return _context

# --- MCP Server Setup ---

mcp = FastMCP("LinkedIn MCP Pro Max")

# Auto-discover all components
import tools  # noqa: F401
discover_all()

@mcp.lifespan()
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage MCP server lifecycle."""
    ctx = await get_ctx()
    try:
        await ctx.initialize_browser()
        logger.info("MCP server lifespan started.")
    except Exception as exc:
        logger.warning(f"Lifespan init failed: {exc}")

    yield

    if ctx.browser:
        await ctx.browser.close()
        logger.info("MCP server lifespan ended.")

# --- CLI Lifecycle Handlers ---

async def run_session_commands(settings: Settings) -> bool:
    """Handle CLI commands: login, status, logout."""
    ctx = await get_ctx()
    await ctx.initialize_browser()
    auth = AuthResolver(ctx.browser, ctx.sessions)

    # Note: CLI settings might differ from Settings singleton if passed via click/argparse
    # but here we assume the passed 'settings' is what we should check for flags
    if getattr(settings, 'logout', False):
        success = await auth.logout()
        import sys
        sys.stderr.write("Logged out successfully.\n" if success else "Logout failed.\n")
        return True

    if getattr(settings, 'status', False):
        is_auth = await auth.is_authenticated()
        import sys
        sys.stderr.write(f"Authenticated: {is_auth}\n")
        return True

    if getattr(settings, 'login', False):
        success = await auth.login()
        import sys
        sys.stderr.write("Login successful.\n" if success else "Login failed.\n")
        return True

    return False
