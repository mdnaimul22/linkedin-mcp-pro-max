"""Database layer entry point.

Dependency Rule:
    imports FROM: .database
    MUST NOT import: services, api, browser, session, tools, app, config
"""

from .database import DatabaseService

__all__ = ["DatabaseService"]
