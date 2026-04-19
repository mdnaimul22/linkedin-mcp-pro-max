"""
LinkedIn MCP Pro Max — Composition Root
========================================
Instantiates and connects all application layers via the Unified Component Registry.

Architecture
------------
All services are auto-discovered from `services/` and wired into AppContext at
startup. No manual imports or field declarations are needed when adding new
services — simply add a `SERVICE = ServiceMeta(...)` marker to the module.

Lifecycle
---------
1. `get_ctx()` → creates AppContext singleton, wires eager services.
2. `AppContext.initialize_browser()` → starts browser, wires lazy services.
3. `app_lifespan()` → manages graceful shutdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator

from fastmcp import FastMCP

from config.settings import Settings, get_settings
from api.linkedin import LinkedInClient
from browser.manager import BrowserManager, create_browser
from browser.session import SessionManager
from providers import BaseProvider, ClaudeProvider, OpenAIProvider
from providers.image import ImageProvider
from api.executor import ApiExecutor
from services.helpers import JSONCache

# Type-only imports for IDE support (no runtime cost)
if TYPE_CHECKING:
    from services.profile import ProfileService
    from services.jobs import JobSearchService
    from services.tracker import ApplicationTrackerService
    from services.resume import ResumeGeneratorService
    from services.cover_letter import CoverLetterGeneratorService
    from services.content import ContentService
    from services.profile_analyzer import ProfileAnalyzerService
    from services.template import TemplateManager

logger = logging.getLogger("linkedin-mcp-pro-max.app")


@dataclass
class AppContext:
    """
    Central Dependency Injection (DI) container.

    All services are wired automatically via the registry — no manual
    field declarations needed for new services. Infrastructure components
    (browser, AI provider) are managed explicitly as they have
    complex lifecycle requirements.

    Service access:
        ctx = await get_ctx()
        profiles = ctx.profiles          # auto-wired ProfileService
        resume_gen = ctx.resume_gen      # auto-wired ResumeGeneratorService
    """

    settings: Settings
    sessions: SessionManager
    client: LinkedInClient
    cache: JSONCache = field(init=False)
    ai: BaseProvider | None = field(init=False)
    image_provider: ImageProvider | None = field(init=False)

    # Infrastructure components (managed explicitly)
    browser: BrowserManager | None = field(default=None)
    api_executor: ApiExecutor | None = field(default=None)

    def __post_init__(self) -> None:
        """Bootstrap the AI provider and auto-wire all eager services."""

        # ── Core Infrastructure ────────────────────────────────────────────
        self.cache = JSONCache(self.settings.data_dir / "cache")

        # ── AI Provider ────────────────────────────────────────────────────
        provider_type = self.settings.ai_provider.lower()
        if provider_type == "openai" and self.settings.openai_api_key:
            self.ai = OpenAIProvider(
                api_key=self.settings.openai_api_key.get_secret_value(),
                model=self.settings.ai_model,
                api_base=self.settings.ai_base_url or None,
            )
        elif provider_type == "claude" and self.settings.anthropic_api_key:
            self.ai = ClaudeProvider(
                api_key=self.settings.anthropic_api_key.get_secret_value(),
                model=self.settings.ai_model,
            )
        else:
            self.ai = None

        # ── Image Generation Provider (Google Gemini) ─────────────────────────
        if self.settings.has_image_gen:
            self.image_provider = ImageProvider(
                api_key=self.settings.gemini_api_key,
                model=self.settings.gemini_image_model,
            )
        else:
            self.image_provider = None

        # ── Auto-Wire Eager Services ───────────────────────────────────────
        # The registry scans services/ and instantiates all non-lazy services.
        self._wire_services(lazy=False)

    def _wire_services(self, lazy: bool) -> None:
        """
        Wire services from the registry using multi-pass resolution.

        Services with factory lambdas may reference other services on `self`
        that haven't been wired yet (e.g., cover_letter_gen → ctx.profiles).
        A multi-pass approach retries failed services until all resolve or
        no further progress can be made.

        Args:
            lazy: If True, wire only lazy (browser-dependent) services.
                  If False, wire only eager (startup-time) services.
        """
        from helpers.registry import get_services

        pending = [m for m in get_services() if m.lazy == lazy]
        max_passes = len(pending) + 1  # guaranteed to converge

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
                    logger.debug("Wired service: %s → %s (pass %d)", meta.attr, meta.cls.__name__, pass_num)
                except Exception as exc:
                    still_pending.append((meta, exc))

            if not still_pending:
                break  # all wired
            if len(still_pending) == len(pending):
                # No progress — log remaining failures and stop
                for meta, exc in still_pending:
                    logger.error(
                        "Failed to wire service '%s' (%s): %s",
                        meta.attr,
                        meta.cls.__name__,
                        exc,
                    )
                break
            pending = [m for m, _ in still_pending]

    async def initialize_browser(self) -> None:
        """
        Provision the stealth browser automation layer.

        After the browser starts, all lazy (browser-dependent) services
        are wired with the live browser instance.
        """
        if self.browser:
            return

        self.browser = await create_browser(
            session_manager=self.sessions,
            headless=self.settings.headless,
            cdp_url=self.settings.cdp_url,
            viewport_width=self.settings.viewport_width,
            viewport_height=self.settings.viewport_height,
            slow_mo=self.settings.slow_mo,
        )

        # Wire lazy services now that browser is available
        self._wire_services(lazy=True)

        # Attach sniffer to API client for cross-layer network logging
        self.api_executor = ApiExecutor(
            page=self.browser.page,
            registry_path=self.settings.data_dir / "api_cookbook.json",
        )
        if self.browser.sniffer:
            self.client.sniffer = self.browser.sniffer

        logger.info("Browser initialized and lazy services wired.")


# ── Global Singleton ───────────────────────────────────────────────────────────

_context: AppContext | None = None


async def get_ctx() -> AppContext:
    """Retrieve or lazily initialize the global AppContext singleton."""
    global _context
    if not _context:
        settings = get_settings()
        sessions = SessionManager(settings)
        client = LinkedInClient(settings)
        _context = AppContext(settings, sessions, client)
    return _context


# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = FastMCP("LinkedIn MCP Pro Max")

# ── Bootstrap: Run discovery and register all components ──────────────────────
# Order matters:
#   1. discover_all() populates the service/actor/scraper registries.
#   2. `import tools` triggers tool autodiscovery (tools/__init__.py).
from helpers.registry import discover_all  # noqa: E402
discover_all()

import tools  # noqa: E402, F401  — triggers tools/__init__.py discovery


# ── Lifespan ──────────────────────────────────────────────────────────────────

@mcp.lifespan()
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage MCP server startup and graceful shutdown."""
    yield

    # Graceful shutdown
    ctx = await get_ctx()
    if ctx.browser:
        await ctx.browser.close()


# ── CLI Session Commands ───────────────────────────────────────────────────────

async def run_session_commands(settings: Settings) -> bool:
    """Handle CLI lifecycle commands: --login, --login-auto, --status, --logout."""
    from services.auth import AuthResolver

    ctx = await get_ctx()
    await ctx.initialize_browser()
    auth = AuthResolver(ctx.browser, ctx.sessions)

    if settings.logout:
        success = await auth.logout()
        print("Logged out successfully." if success else "Logout failed.")
        return True

    if settings.status:
        is_auth = await auth.is_authenticated()
        print(f"Authenticated: {is_auth}")
        return True

    if settings.login_auto:
        success = await auth.login_automated()
        print("Automated login successful." if success else "Automated login failed.")
        return True

    if settings.login:
        success = await auth.login_interactively()
        if not success:
            print("Interactive login failed.")
        return True

    return False
