"""
LinkedIn MCP Pro Max - CLI Entry Point
This script handles configuration, authentication commands, and starts the server.
"""

import logging
import argparse
import sys
import asyncio
import threading
from pathlib import Path

from app import mcp, run_session_commands
from config.settings import get_settings, set_settings


def main():
    """Configure environment and execute the LinkedIn MCP Pro Max service."""
    
    # Initial basic logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    
    settings = get_settings()

    # Apply log level from environment/config
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)

    logger = logging.getLogger("linkedin-mcp-pro-max.main")

    # Command Line Interface Setup
    parser = argparse.ArgumentParser(
        description="🌐 LinkedIn MCP Pro Max - Next-Gen User Agent for AI Workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  linkedin-mcp-pro-max --login-auto        # Run automated headless login
  linkedin-mcp-pro-max --status            # Check current auth status
  linkedin-mcp-pro-max --no-headless       # Start server in windowed mode
        """
    )

    # Authentication & Session Commands
    auth_group = parser.add_argument_group("Authentication & Sessions")
    auth_group.add_argument(
        "--login", action="store_true", help="Start interactive browser login (windowed)"
    )
    auth_group.add_argument(
        "--login-auto", action="store_true", help="Start autonomous headless login"
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

    # Parse args (allow passthrough for future FastMCP/Click compatibility)
    args, _ = parser.parse_known_args()

    # Map CLI arguments to settings model
    updates = {
        "login": args.login,
        "status": args.status,
        "logout": args.logout,
        "login_auto": args.login_auto,
    }
    if args.headless is not None:
        updates["headless"] = args.headless
    if args.cdp_url:
        updates["cdp_url"] = args.cdp_url

    # Update global settings singleton
    settings = settings.model_copy(update=updates)
    set_settings(settings)

    # Validate essential configuration
    errors = settings.validate_config()
    if errors:
        logger.warning(f"Configuration advisory: {', '.join(errors)}")

    # Execute session-specific commands if requested
    if any([settings.login, settings.login_auto, settings.status, settings.logout]):
        logger.info("Executing lifecycle command...")
        was_session_cmd = asyncio.run(run_session_commands(settings))
        if was_session_cmd:
            return

    # Start the MCP Server
    logger.info("Initializing LinkedIn MCP Pro Max Server...")
    
    if args.dev:
        try:
            from watchfiles import watch
            
            def run_watcher(src_dir: str):
                watcher_logger = logging.getLogger("linkedin-mcp.watcher")
                watcher_logger.info(f"Auto-reload enabled: Watching {src_dir} for changes...")
                for changes in watch(src_dir):
                    watcher_logger.info(f"Detected changes: {changes}. Restarting server...")
                    sys.exit(0)
                    
            src_path = str(Path(__file__).parent.absolute())
            threading.Thread(target=run_watcher, args=(src_path,), daemon=True).start()
        except ImportError:
            logger.error("watchfiles is not installed. Run 'uv pip install watchfiles'")
            
    mcp.run()


if __name__ == "__main__":
    main()

