import asyncio
import json
import sys
import os

# Add 'src' to sys.path to allow imports from there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from app import mcp, get_ctx
import tools
from helpers.registry import discover_all

async def test_profile_tool():
    print("Forcing tool discovery...")
    tools.discover_tools()
    discover_all()
    
    print("Initializing context and browser...")
    ctx = await get_ctx()
    await ctx.initialize_browser()
    
    print("Calling 'profile' tool for 'me'...")
    try:
        # Use mcp.call_tool
        result = await mcp.call_tool("profile", {"action": "get", "profile_id": "me"})
        print("\n--- Tool Output ---")
        print(result)
        print("-------------------\n")
    except Exception as e:
        print(f"Error calling tool: {e}")
    finally:
        if ctx.browser:
            await ctx.browser.close()

if __name__ == "__main__":
    asyncio.run(test_profile_tool())
