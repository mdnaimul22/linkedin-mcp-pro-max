"""Global custom exceptions for LinkedIn MCP server.

This module is the single source of truth for all custom error classes.
It intentionally has ZERO local project imports — only standard library types.
Every other module (api, browser, session, providers, services, tools) imports from here.
"""

from typing import Any


class LinkedInMCPError(Exception):
    """Base class for all exceptions in the LinkedIn MCP server."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(LinkedInMCPError):
    """Raised when there is an issue with the application configuration."""


class AuthenticationError(LinkedInMCPError):
    """Raised when authentication with LinkedIn fails."""


class LinkedInAPIError(LinkedInMCPError):
    """Raised when the LinkedIn API returns an error or unexpected response."""


class NetworkError(LinkedInMCPError):
    """Raised when there is a network-level failure during browser operations."""


class RateLimitError(LinkedInMCPError):
    """Raised when LinkedIn rate-limiting or security challenges are detected."""

    def __init__(
        self, message: str = "Rate limit exceeded", suggested_wait_time: int = 60
    ):
        self.suggested_wait_time = suggested_wait_time
        super().__init__(message, {"suggested_wait_time": suggested_wait_time})


class NotFoundError(LinkedInMCPError):
    """Raised when a requested resource (profile, job, etc.) cannot be found."""

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            {"resource_type": resource_type, "resource_id": resource_id},
        )


class AIProviderError(LinkedInMCPError):
    """Raised when an AI provider (Claude, OpenAI) fails to process a request."""


class TemplateError(LinkedInMCPError):
    """Raised when there is an error in prompt template rendering."""


class BrowserError(LinkedInMCPError):
    """Raised when a low-level browser automation error occurs."""


class ElementNotFoundError(BrowserError):
    """Raised when a required UI element is not found on the page."""
