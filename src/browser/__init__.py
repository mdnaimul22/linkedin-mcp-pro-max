"""browser/ package — Playwright browser automation layer.

Dependency Rule:
  imports FROM: exceptions, schema, session, browser/helpers, helpers(global)
  MUST NOT import: api, providers, services, tools
"""

from .helpers.driver import BrowserDriver
from .manager import (
    Manager,
    create_browser,
)
from .helpers import (
    stabilize_navigation,
    scroll_to_bottom,
    handle_modal_close,
    detect_rate_limit,
    wait_for_any_selector,
    get_page_content,
)
from .actors.auth import (
    handle_login_form,
    validate_linkedin_auth,
    export_linkedin_cookies,
)

__all__ = [
    "BrowserDriver",
    "Manager",
    "create_browser",
    "validate_linkedin_auth",
    "export_linkedin_cookies",
    "handle_login_form",
    "handle_modal_close",
    "detect_rate_limit",
    "stabilize_navigation",
    "scroll_to_bottom",
    "wait_for_any_selector",
    "get_page_content",
]
