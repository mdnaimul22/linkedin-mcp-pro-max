import os
import asyncio
import logging
from app import mcp

logger = logging.getLogger("linkedin-mcp.tools.system")


@mcp.tool()
async def restart_server() -> str:
    """Restart the MCP server. Use this tool if you need to load new code changes or if the server gets stuck.
    The MCP client will automatically restart the process, so it will come back online shortly.
    """
    logger.info("Server restart requested via tool. Exiting in 1 second...")
    
    async def _delayed_exit():
        await asyncio.sleep(1.0)
        os._exit(0)
    
    # Schedule the exit to happen after the response is sent back
    asyncio.create_task(_delayed_exit())
    
    return "Server is restarting... Please wait a moment for it to come back online."
