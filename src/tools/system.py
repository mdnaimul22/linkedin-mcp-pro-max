import os
import asyncio
import logging
from app import mcp

from typing import Literal
from fastmcp.exceptions import ToolError

logger = logging.getLogger("linkedin-mcp.tools.system")


@mcp.tool()
async def server(
    action: Literal["restart"],
    reason: str = "User requested restart",
) -> str:
    """Manage the MCP server.
    
    Args:
        action: The server action to perform ('restart'),
        reason: Optional reason for the restart,
        
    allowed_args_for_action = {
        "restart": ["reason"]
    }
    """
    try:
        allowed_args = {
            "restart": ["reason"]
        }
        provided = []
        if reason != "User requested restart":
            provided.append("reason")
        
        for arg in provided:
            if arg not in allowed_args.get(action, []):
                raise ToolError(f"Argument '{arg}' is not allowed for action '{action}'. Allowed arguments: {allowed_args.get(action, [])}")

        if action == "restart":
            logger.info(f"Server restart requested via tool. Reason: {reason}. Exiting in 1 second...")
            
            async def _delayed_exit():
                await asyncio.sleep(1.0)
                os._exit(0)
            
            # Schedule the exit to happen after the response is sent back
            asyncio.create_task(_delayed_exit())
            
            return "Server is restarting... Please wait a moment for it to come back online."
            
        else:
            raise ToolError(f"Unknown action: {action}")
            
    except Exception as e:
        raise ToolError(str(e))
