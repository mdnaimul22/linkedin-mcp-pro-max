"""
Configuration system for LinkedIn MCP Server.

Provides a unified settings management using Pydantic BaseSettings.
"""

import logging

from .settings import Settings, get_settings, set_settings
from . import prompts

logger = logging.getLogger(__name__)

__all__ = [
    "Settings",
    "get_settings",
    "set_settings",
    "prompts",
]
