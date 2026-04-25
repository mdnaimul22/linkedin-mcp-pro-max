from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Callable, Type

logger = logging.getLogger("linkedin-mcp-pro-max.registry")


@dataclass
class ServiceMeta:
    attr: str
    cls: Type
    deps: list[str] = field(default_factory=list)
    lazy: bool = False
    factory: Callable | None = None


@dataclass
class ActorMeta:
    attr: str
    cls: Type


@dataclass
class ScraperMeta:
    attr: str
    cls: Type


_SERVICE_REGISTRY: list[ServiceMeta] = []
_ACTOR_REGISTRY: list[ActorMeta] = []
_SCRAPER_REGISTRY: list[ScraperMeta] = []
_discovered: bool = False  # Guard: discover_all() runs exactly once


def _scan_package(
    package_dir: str,
    package_name: str,
    meta_attr: str,
    expected_type: type,
    registry: list,
    skip: set[str] | None = None,
) -> None:
    
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


def get_services() -> list[ServiceMeta]:
    """Return all discovered service descriptors."""
    return _SERVICE_REGISTRY


def get_actors() -> list[ActorMeta]:
    """Return all discovered actor descriptors."""
    return _ACTOR_REGISTRY


def get_scrapers() -> list[ScraperMeta]:
    """Return all discovered scraper descriptors."""
    return _SCRAPER_REGISTRY
