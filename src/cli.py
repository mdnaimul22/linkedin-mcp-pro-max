"""
LinkedIn MCP Pro Max - CLI Entry Point
This script handles configuration, authentication commands, and starts the server.
"""

import os
import sys

# Silence third-party stdout pollution (e.g. fastmcp update checks and banner)
# These MUST be set before FastMCP is imported via 'app'
os.environ["FAST_MCP_CHECK_UPDATES"] = "0"
os.environ["FAST_MCP_BANNER"] = "0"

import argparse
import asyncio
import threading

from app import mcp, run_session_commands
from config import Settings, setup_logger, set_settings

def main():
    """Configure environment and execute the LinkedIn MCP Pro Max service."""
    
    # Initialize unified logger
    logger = setup_logger(Settings.LOG_DIR / "main.log", name="linkedin-mcp-pro-max.main")

    # Command Line Interface Setup
    parser = argparse.ArgumentParser(
        description="🌐 LinkedIn MCP Pro Max - Next-Gen User Agent for AI Workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  linkedin-mcp-pro-max --login             # Run automated headless login
  linkedin-mcp-pro-max --status            # Check current auth status
  linkedin-mcp-pro-max --no-headless       # Start server in windowed mode
        """
    )

    # Authentication & Session Commands
    auth_group = parser.add_argument_group("Authentication & Sessions")
    auth_group.add_argument(
        "--login", action="store_true", help="Start autonomous headless login"
    )
    auth_group.add_argument(
        "--status", action="store_true", help="Check current LinkedIn authentication status"
    )
    auth_group.add_argument(
        "--logout", action="store_true", help="Clear stored session data and cookies"
    )

    # Browser & Environment Overrides
    browser_group = parser.add_argument_group("Browser & Environment Overrides")
    browser_group.add_argument(
        "--dev", action="store_true", help="Start server in development mode (auto-reload on code changes)"
    )
    browser_group.add_argument(
        "--headless", action="store_true", default=None, help="Force headless execution"
    )
    browser_group.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Force windowed (no-headless) execution",
    )
    browser_group.add_argument(
        "--cdp-url", type=str, help="Connect to an existing browser via CDP URL"
    )

    # If no arguments provided, show help on stderr but continue to start server
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)

    # Parse args (allow passthrough for future FastMCP/Click compatibility)
    args, _ = parser.parse_known_args()

    # Map CLI arguments to settings model
    updates = {
        "status": args.status,
        "logout": args.logout,
        "login": args.login,
    }
    if args.headless is not None:
        updates["headless"] = args.headless
    if args.cdp_url:
        updates["cdp_url"] = args.cdp_url

    # Update global settings singleton
    global_settings = Settings.model_copy(update=updates)
    set_settings(global_settings)

    # Validate essential configuration
    errors = global_settings.validate_config()
    if errors:
        logger.warning(f"Configuration advisory: {', '.join(errors)}")

    # Execute session-specific commands if requested
    if any([global_settings.login, global_settings.status, global_settings.logout]):
        logger.info("Executing lifecycle command...")
        was_session_cmd = asyncio.run(run_session_commands(global_settings))
        if was_session_cmd:
            return

    # Start the MCP Server
    logger.info("Initializing LinkedIn MCP Pro Max Server...")
    
    if args.dev:
        try:
            from watchfiles import watch
            
            def run_watcher(src_dir: str):
                watcher_logger = setup_logger(Settings.LOG_DIR / "watcher.log", name="linkedin-mcp.watcher")
                watcher_logger.info(f"Auto-reload enabled: Watching {src_dir} for changes...")
                for changes in watch(src_dir):
                    watcher_logger.info(f"Detected changes: {changes}. Restarting server...")
                    sys.exit(0)
                    
            src_path = os.path.dirname(os.path.abspath(__file__))
            threading.Thread(target=run_watcher, args=(src_path,), daemon=True).start()
        except ImportError:
            logger.error("watchfiles is not installed. Run 'uv pip install watchfiles'")
            
    mcp.run(show_banner=False, log_level="WARNING")


if __name__ == "__main__":
    main()
