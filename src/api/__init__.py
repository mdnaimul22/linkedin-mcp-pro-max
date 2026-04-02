"""api/ package — LinkedIn API client layer.

Dependency Rule:
  imports FROM: config, schema, exceptions, api/helpers
  MUST NOT import: browser, session, providers, services, tools
"""

from .linkedin import LinkedInClient
from .executor import ApiExecutor

__all__ = ["LinkedInClient", "ApiExecutor"]
