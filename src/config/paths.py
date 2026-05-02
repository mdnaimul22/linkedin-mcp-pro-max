import sys
from pathlib import Path

_MARKER_FILES = ("pyproject.toml", ".git", ".env", "requirements.txt", "setup.py")

def find_project_root() -> Path:
    """
    Find the project root by searching upwards for marker files.
    Standardizes the project root to the directory containing pyproject.toml, .git, etc.
    """
    current = Path(__file__).resolve().parent
    # Search from the directory of this file upwards
    for candidate in [current] + list(current.parents):
        if any((candidate / m).exists() for m in _MARKER_FILES):
            return candidate
    
    # Fallback to the parent of the 'src' directory if we are inside it
    if current.name == "config" and current.parent.name == "src":
        return current.parent.parent
        
    return current.parent

PROJECT_ROOT = find_project_root()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
