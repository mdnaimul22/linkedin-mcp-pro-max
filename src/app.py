"""
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
import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncIterator

from fastmcp import FastMCP

from config.settings import Settings, get_settings
from providers.linkedin import LinkedInClient
from browser.manager import Manager, create_browser
from browser.session import Session
from providers import BaseProvider, ClaudeProvider, OpenAIProvider
from providers.image import ImageProvider
from browser.helpers.executor import ApiExecutor
from services.helpers import JSONCache
from helpers.registry import discover_all, get_services

if TYPE_CHECKING:
    pass

logger = logging.getLogger("linkedin-mcp-pro-max.app")


@dataclass
class AppContext:

    settings: Settings
    sessions: Session
    client: LinkedInClient
    lock: asyncio.Lock = field(init=False)
    cache: JSONCache = field(init=False)
    ai: BaseProvider | None = field(init=False)
    image_provider: ImageProvider | None = field(init=False)
    browser: Manager | None = field(default=None)
    api_executor: ApiExecutor | None = field(default=None)

    def __post_init__(self) -> None:
        self.lock = asyncio.Lock()
        self.cache = JSONCache(self.settings.data_dir / "cache")

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

        if self.settings.has_image_gen:
            self.image_provider = ImageProvider(
                api_key=self.settings.gemini_api_key,
                model=self.settings.gemini_image_model,
            )
        else:
            self.image_provider = None

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
                # No progress — circular dependency detected, fail fast
                failed = [(m.attr, m.cls.__name__, str(exc)) for m, exc in still_pending]
                details = "; ".join(f"{attr} ({cls}): {err}" for attr, cls, err in failed)
                raise RuntimeError(
                    f"Circular or unresolvable service dependency detected — "
                    f"no progress after pass {pass_num}. Failed services: {details}"
                )
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

        self._wire_services(lazy=True)

        self.api_executor = ApiExecutor(
            page=self.browser.page,
            registry_path=self.settings.data_dir / "api_cookbook.json",
        )
        self.browser.set_api_executor(self.api_executor)

        logger.info("Browser initialized — ready for field discovery.")

_context: AppContext | None = None

async def get_ctx() -> AppContext:
    """Retrieve or lazily initialize the global AppContext singleton."""
    global _context
    if not _context:
        settings = get_settings()
        sessions = Session(settings)
        client = LinkedInClient(settings)
        _context = AppContext(settings, sessions, client)
    return _context


mcp = FastMCP("LinkedIn MCP Pro Max")

import tools  # Register all MCP tools
discover_all()

@mcp.lifespan()
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage MCP server startup and graceful shutdown.

    Startup: initialize browser + bind sniffer + start DiscoveryPipeline.
    Shutdown: stop pipeline + close browser gracefully.
    """
    ctx = await get_ctx()

    try:
        await ctx.initialize_browser()
        logger.info("Lifespan: browser ready — DiscoveryPipeline running in background.")
    except Exception as exc:
        logger.warning("Lifespan: browser init failed (%s) — pipeline not started.", exc)

    yield

    if ctx.browser:
        await ctx.browser.close()


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

    return False
