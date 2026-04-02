"""
Modules are discovered and imported dynamically at runtime.
"""

import pkgutil
import importlib
import logging
from pathlib import Path

logger = logging.getLogger("linkedin-mcp-pro-max.tools")


def discover_tools():
    """Autodiscover and import all tool modules in this package."""
    # The absolute path to this tools directory
    package_path = [str(Path(__file__).parent)]

    for _, module_name, is_pkg in pkgutil.walk_packages(package_path):
        # Skip init and non-functional helpers, and subpackages
        if module_name in ("__init__", "helpers") or is_pkg:
            continue

        try:
            # Dynamically import the module to trigger tool registration
            importlib.import_module(f".{module_name}", package=__name__)
            # logger.debug(f"Successfully loaded tool module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load tool module {module_name}: {e}")


# Trigger discovery on package import
discover_tools()

