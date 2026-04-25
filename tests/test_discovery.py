import asyncio
import sys
import os
import json

# Ensure src is in the path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from app import get_ctx

async def main():
    ctx = await get_ctx()
    await ctx.initialize_browser()

    # URL to analyze - e.g. the main profile page or a specific section
    # For testing, we'll try the authenticated user's profile
    url = "https://www.linkedin.com/in/me/"
    
    print(f"\n--- Discovering Fields at {url} ---")
    
    # Use the newly refactored ApiExecutor (now Field Discovery Engine)
    results = await ctx.api_executor.execute(url)
    
    if not results.success:
        print(f"Error: {results.error}")
    else:
        print(f"Summary: {json.dumps(results.summary.model_dump(), indent=2)}")
        
        # Print a few example inputs
        if results.inputs:
            print("\nTop 5 Inputs found:")
            for i in results.inputs[:5]:
                print(f" - ID: {i.id}, Name: {i.name}, Label: {i.label}, Placeholder: {i.placeholder}")

        if results.buttons:
            print("\nTop 5 Buttons found:")
            for b in results.buttons[:5]:
                # Assuming button text might be captured in label or value
                print(f" - ID: {b.id}, Value/Label: {b.label or b.value}, Aria-Label: {b.aria_label}")

if __name__ == "__main__":
    asyncio.run(main())
