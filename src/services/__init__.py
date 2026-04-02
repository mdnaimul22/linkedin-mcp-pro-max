"""services/ package — business logic orchestration layer.

Dependency Rule:
  imports FROM: helpers.models, api, browser, session, providers, services/helpers, exceptions
  MUST NOT import: tools (tool layer is the consumer, not the dependency)

Discovery:
  All services are auto-discovered by `helpers.registry.discover_all()` at startup.
  Each service module declares a `SERVICE = ServiceMeta(...)` convention marker.
  No manual registration in this file is needed when adding new services.
"""

# Re-export the cache helper (used directly by tools and other services)
from .helpers import JSONCache  # noqa: F401

__all__ = ["JSONCache"]
