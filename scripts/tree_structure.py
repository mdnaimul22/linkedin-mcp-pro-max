#!/usr/bin/env python3
"""
gen_structure.py - Project Structure Visualizer

Usage:
    python gen_structure.py <target_dir> [-v | -h]

Output:
    <target_dir>/.agent/rules/project_structure.md
"""

import sys
import re
import ast
from pathlib import Path

# ─────────────────────────────────────────────
# ANSI Colors
# ─────────────────────────────────────────────

class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[36m"
    YELLOW  = "\033[33m"
    GREEN   = "\033[32m"
    MAGENTA = "\033[35m"
    GRAY    = "\033[90m"

def c(text, *codes):
    return "".join(codes) + text + Color.RESET

# ─────────────────────────────────────────────
# Ignore Rules — তোমার original values
# ─────────────────────────────────────────────

DEFAULT_IGNORED_NAMES = {
    "__pycache__", ".env", ".venv", ".npm", ".git", ".DS_Store",
    "node_modules", "dist", "build", "coverage",
    ".idea", ".vscode", ".gemini",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Gemfile.lock",
    ".pytest_cache", ".mypy_cache", ".tox", ".egg-info",
}

SKIPPED_PATHS = {
    "/home/openscore/a0/usr/projects/linkedin-mcp-pro-max/src/linkedin_scraper_mcp.egg-info"
    "/home/openscore/a0/usr/projects/linkedin-mcp-pro-max/build",
    "/home/openscore/a0/usr/projects/linkedin-mcp-pro-max/.venv",
    "/home/openscore/a0/usr/projects/linkedin-mcp-pro-max/.ruff_cache",
    "/home/openscore/a0/usr/projects/linkedin-mcp-pro-max/.pytest_cache",
    "/home/openscore/a0/usr/projects/linkedin-mcp-pro-max/.gemini",
}

DEFAULT_IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
    ".iso", ".tar", ".gz", ".zip",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico", ".webp",
    ".svg", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3",
    ".pdf",
    ".lock", ".log", ".tmp", ".bak", ".swp", ".swo",
    ".html", ".css",
}

def should_skip(item: Path) -> bool:
    name     = item.name
    resolved = str(item.resolve())
    if name in DEFAULT_IGNORED_NAMES:
        return True
    if resolved in SKIPPED_PATHS:
        return True
    if item.suffix.lower() in DEFAULT_IGNORED_EXTENSIONS:
        return True
    if name.startswith(".") and name not in {".env.example", ".editorconfig"}:
        return True
    return False

def children(path: Path) -> list:
    try:
        items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except (PermissionError, FileNotFoundError):
        return []
    return [i for i in items if not should_skip(i)]

# ─────────────────────────────────────────────
# Phase 1: Scan all paths → build keyword set
# ─────────────────────────────────────────────

def scan_paths(dir_path: Path, result=None) -> list:
    if result is None:
        result = []
    for item in children(dir_path):
        if item.is_dir():
            scan_paths(item, result)
        else:
            result.append(item.resolve())
    return result

# Python stdlib + common installed libraries
# These are excluded even if they appear as folder/file names in project
STDLIB_BLACKLIST = {
    "logging", "os", "sys", "re", "ast", "json", "types",
    "typing", "pathlib", "abc", "io", "time", "datetime",
    "collections", "functools", "itertools", "operator",
    "threading", "subprocess", "shutil", "tempfile",
    "hashlib", "hmac", "base64", "uuid", "copy",
    "math", "random", "string", "struct", "socket",
    "http", "email", "html", "xml", "csv", "enum",
    "dataclasses", "contextlib", "warnings", "inspect",
    "traceback", "unittest", "asyncio", "concurrent",
    # common installed libraries
    "alembic", "fastapi", "sqlalchemy", "pydantic",
    "starlette", "uvicorn", "pytest", "requests",
    "httpx", "aiohttp", "celery", "redis", "boto3",
    "numpy", "pandas", "flask", "django", "tornado",
    "jwt", "bcrypt", "cryptography", "passlib",
    "stripe", "twilio", "sendgrid", "openai",
    "anthropic", "langchain", "next", "react",
    "axios", "lodash", "express", "webpack",
}

def build_keywords(all_paths: list, root: Path) -> set:
    keywords = {root.name}
    for path in all_paths:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        for part in rel.parts:
            stem = Path(part).stem
            if (
                len(stem) > 1
                and not stem.startswith("__")
                and stem not in STDLIB_BLACKLIST
            ):
                keywords.add(stem)
    return keywords

# ─────────────────────────────────────────────
# Phase 2: Local import detection
# ─────────────────────────────────────────────

def is_local(module: str, kw: set) -> bool:
    if not module:
        return False
    if module.startswith("."):
        return True
    return module.split(".")[0] in kw

def scan_py(filepath: Path, kw: set) -> list:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8", errors="ignore"))
        result = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if is_local(a.name, kw):
                        result.append(a.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    result.append("." * node.level + (node.module or ""))
                elif node.module and is_local(node.module, kw):
                    result.append(node.module)
        return sorted(set(result))
    except Exception:
        return []

def scan_js(filepath: Path, kw: set) -> list:
    try:
        src = filepath.read_text(encoding="utf-8", errors="ignore")
        all_imp = set(
            re.findall(r"""(?:import|from)\s+['"]([^'"]+)['"]""", src) +
            re.findall(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", src)
        )
        return sorted(i for i in all_imp if i.startswith(".") or is_local(i, kw))
    except Exception:
        return []

def get_imports(filepath: Path, kw: set) -> list:
    ext = filepath.suffix.lower()
    if ext == ".py":
        return scan_py(filepath, kw)
    if ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return scan_js(filepath, kw)
    return []

# ─────────────────────────────────────────────
# Phase 3: Tree render
# ─────────────────────────────────────────────

def render_md(dir_path: Path, kw: set, prefix="") -> list:
    lines = []
    items = children(dir_path)
    for i, item in enumerate(items):
        last = i == len(items) - 1
        con  = "└── " if last else "├── "
        ext  = "    " if last else "│   "
        if item.is_dir():
            lines.append(f"{prefix}{con}{item.name}/")
            lines.extend(render_md(item, kw, prefix + ext))
        else:
            fp  = str(item.resolve())
            imp = get_imports(item, kw)
            if imp:
                s = ", ".join(imp[:6])
                if len(imp) > 6:
                    s += f" +{len(imp)-6} more"
                lines.append(f"{prefix}{con}{fp}  # {s}")
            else:
                lines.append(f"{prefix}{con}{fp}")
    return lines

def render_terminal(dir_path: Path, kw: set, prefix=""):
    items = children(dir_path)
    for i, item in enumerate(items):
        last = i == len(items) - 1
        con  = c("└── " if last else "├── ", Color.GRAY)
        ext  = "    " if last else "│   "
        if item.is_dir():
            print(f"{prefix}{con}{c(item.name+'/', Color.CYAN, Color.BOLD)}")
            render_terminal(item, kw, prefix + c(ext, Color.GRAY))
        else:
            fp  = str(item.resolve())
            imp = get_imports(item, kw)
            hint = c(f"  # {', '.join(imp[:4])}", Color.MAGENTA) if imp else ""
            print(f"{prefix}{con}{c(fp, Color.GREEN)}{hint}")

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    target = Path(args[0]).resolve()
    if not target.exists() or not target.is_dir():
        print(f"Error: '{args[0]}' is not a valid directory.")
        sys.exit(1)

    output = target / ".agents" / "rules" / "project_structure.md"

    # Phase 1: scan paths → keywords
    print(c(f"\n⚡ Scanning {target}...\n", Color.CYAN))
    all_paths = scan_paths(target)
    kw        = build_keywords(all_paths, target)
    print(c(f"   {len(all_paths)} files · {len(kw)} local keywords\n", Color.GRAY))

    # Phase 2+3: terminal preview
    print(c(f"{target.name}/", Color.YELLOW, Color.BOLD))
    render_terminal(target, kw)

    # Write md
    md_lines = render_md(target, kw)
    md  = f"# Project Structure\n\n**Root:** `{target}`\n\n```\n{target.name}/\n"
    md += "\n".join(md_lines)
    md += "\n```\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")

    print(f"\n{c('✅ Saved:', Color.GREEN, Color.BOLD)} {output}\n")

if __name__ == "__main__":
    main()