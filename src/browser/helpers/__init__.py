"""browser/helpers package — private utilities for the browser/ module only.

Rule: MUST NOT be imported by any other top-level module.
"""

from .trace import (
    cleanup_trace_dir,
    get_trace_dir,
    mark_trace_for_retention,
    record_page_trace,
    reset_trace_state_for_testing,
    should_keep_traces,
    trace_enabled,
)
from .dom import (
    get_page_content,
    stabilize_navigation,
    is_visible,
    wait_for_any_selector,
    detect_rate_limit,
    scroll_to_bottom,
    handle_modal_close,
    scroll_job_sidebar,
)

__all__ = [
    "cleanup_trace_dir",
    "get_trace_dir",
    "mark_trace_for_retention",
    "record_page_trace",
    "reset_trace_state_for_testing",
    "should_keep_traces",
    "trace_enabled",
    "get_page_content",
    "stabilize_navigation",
    "is_visible",
    "wait_for_any_selector",
    "detect_rate_limit",
    "scroll_to_bottom",
    "handle_modal_close",
    "scroll_job_sidebar",
]
