"""
LinkedIn MCP Pro Max — Unified Component Registry
==================================================
A single, convention-based discovery engine for all three component types:

  ServiceMeta  → auto-wired into AppContext (app.py)
  ActorMeta    → auto-instantiated in BrowserManager (performs write ops)
  ScraperMeta  → auto-instantiated in BrowserManager (performs read ops)

Developer Contract
------------------
To register a new component, add ONE line to the bottom of its module:

  # In services/network.py:
  SERVICE = ServiceMeta(attr="network", cls=NetworkService, deps=["client"])

  # In browser/actors/messaging.py:
  ACTOR = ActorMeta(attr="messaging_actor", cls=MessagingActor)

  # In browser/scrapers/connections.py:
  SCRAPER = ScraperMeta(attr="connections_scraper", cls=ConnectionsScraper)

No other files need to be modified.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Type

logger = logging.getLogger("linkedin-mcp-pro-max.registry")

# ─────────────────────────────────────────────────────────────────────────────
# Meta Descriptors
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ServiceMeta:
    """
    Descriptor for an auto-wired AppContext service.

    Simple dependency injection (most services):
        SERVICE = ServiceMeta(
            attr="profiles",
            cls=ProfileService,
            deps=["client", "db", "browser"],
            lazy=True,   # True = needs browser; wired in initialize_browser()
        )

    Complex wiring via factory (for computed args like data_dir):
        SERVICE = ServiceMeta(
            attr="resume_gen",
            cls=ResumeGeneratorService,
            factory=lambda ctx: ResumeGeneratorService(
                ctx.profiles, ctx.jobs, ctx.ai,
                ctx.template_manager,
                ctx.settings.data_dir / "resumes",
            ),
            lazy=True,
        )
    """

    attr: str
    cls: Type
    deps: list[str] = field(default_factory=list)
    lazy: bool = False
    factory: Callable | None = None


@dataclass
class ActorMeta:
    """
    Descriptor for a browser actor (write / UI-interaction operations).
    Actor classes MUST accept `page: Page` as their sole constructor argument.

    Example:
        ACTOR = ActorMeta(attr="profile_editor", cls=ProfileEditor)
    """

    attr: str
    cls: Type


@dataclass
class ScraperMeta:
    """
    Descriptor for a browser scraper (read / data-extraction operations).
    Scraper classes MUST accept `page: Page` as their sole constructor argument.

    Example:
        SCRAPER = ScraperMeta(attr="profile_scraper", cls=ProfileScraper)
    """

    attr: str
    cls: Type


# ─────────────────────────────────────────────────────────────────────────────
# Global Registries
# ─────────────────────────────────────────────────────────────────────────────

_SERVICE_REGISTRY: list[ServiceMeta] = []
_ACTOR_REGISTRY: list[ActorMeta] = []
_SCRAPER_REGISTRY: list[ScraperMeta] = []
_discovered: bool = False  # Guard: discover_all() runs exactly once


# ─────────────────────────────────────────────────────────────────────────────
# Discovery Engine
# ─────────────────────────────────────────────────────────────────────────────


def _scan_package(
    package_dir: str,
    package_name: str,
    meta_attr: str,
    expected_type: type,
    registry: list,
    skip: set[str] | None = None,
) -> None:
    """
    Walk a Python package directory and collect all components marked with a
    convention attribute (SERVICE / ACTOR / SCRAPER).

    Args:
        package_dir:  Absolute path to the package directory (use pkg.__path__[0]).
        package_name: Dotted import name (e.g. 'services', 'browser.actors').
        meta_attr:    The module-level attribute to look for ('SERVICE', etc).
        expected_type: The Meta class type to validate against.
        registry:     The list to append discovered instances to.
        skip:         Set of module basenames to ignore.
    """
    skip = skip or set()
    package_dir = str(package_dir)

    for finder, name, is_pkg in pkgutil.walk_packages(
        path=[package_dir], prefix=f"{package_name}."
    ):
        basename = name.split(".")[-1]

        # Skip internal, helper, and explicitly excluded modules
        if basename.startswith("_") or basename in skip or is_pkg:
            continue

        try:
            mod = importlib.import_module(name)
            meta = getattr(mod, meta_attr, None)
            if isinstance(meta, expected_type):
                registry.append(meta)
                logger.debug(
                    "[registry] Registered %s '%s' from module '%s'",
                    expected_type.__name__,
                    meta.attr,
                    name,
                )
        except Exception as exc:
            logger.error(
                "[registry] Failed to import '%s' while scanning for %s: %s",
                name,
                meta_attr,
                exc,
            )


def discover_all() -> None:
    """
    Run all discovery routines.

    Safe to call multiple times — idempotent after the first run.
    Called once at application startup before the MCP server is started.
    """
    global _discovered
    if _discovered:
        return
    _discovered = True

    # ── Services ──────────────────────────────────────────────────────────
    import services as _services_pkg

    _scan_package(
        package_dir=_services_pkg.__path__[0],
        package_name="services",
        meta_attr="SERVICE",
        expected_type=ServiceMeta,
        registry=_SERVICE_REGISTRY,
        skip={"auth", "helpers"},  # auth = CLI-only; helpers = utilities
    )

    # ── Browser Actors ────────────────────────────────────────────────────
    import browser.actors as _actors_pkg

    _scan_package(
        package_dir=_actors_pkg.__path__[0],
        package_name="browser.actors",
        meta_attr="ACTOR",
        expected_type=ActorMeta,
        registry=_ACTOR_REGISTRY,
        skip={"auth"},  # auth = infrastructure utility, not an actor
    )

    # ── Browser Scrapers ──────────────────────────────────────────────────
    import browser.scrapers as _scrapers_pkg

    _scan_package(
        package_dir=_scrapers_pkg.__path__[0],
        package_name="browser.scrapers",
        meta_attr="SCRAPER",
        expected_type=ScraperMeta,
        registry=_SCRAPER_REGISTRY,
        skip=set(),  # all scraper files are valid
    )

    logger.info(
        "[registry] Discovery complete — %d service(s) | %d actor(s) | %d scraper(s)",
        len(_SERVICE_REGISTRY),
        len(_ACTOR_REGISTRY),
        len(_SCRAPER_REGISTRY),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public Accessors
# ─────────────────────────────────────────────────────────────────────────────


def get_services() -> list[ServiceMeta]:
    """Return all discovered service descriptors."""
    return _SERVICE_REGISTRY


def get_actors() -> list[ActorMeta]:
    """Return all discovered actor descriptors."""
    return _ACTOR_REGISTRY


def get_scrapers() -> list[ScraperMeta]:
    """Return all discovered scraper descriptors."""
    return _SCRAPER_REGISTRY
