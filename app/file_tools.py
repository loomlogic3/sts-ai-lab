"""
Read-only file tools for STS AI Lab.
"""

from pathlib import Path


BLOCKED_PARTS = {
    ".env",
    ".git",
    "__pycache__",
    "data",
}


def read_file(path_text: str) -> str:
    """
    Safely read a project file.
    """

    path = Path(path_text).expanduser()

    if path.is_absolute():
        return "Blocked: absolute paths are not allowed."

    if any(part in BLOCKED_PARTS for part in path.parts):
        return "Blocked: this path is not allowed."

    if not path.exists():
        return f"File not found: {path}"

    if not path.is_file():
        return f"Not a file: {path}"

    return path.read_text(encoding="utf-8")


def project_tree(max_depth: int = 2) -> str:
    """
    Safely list project files up to a limited depth.
    """

    root = Path(".")
    lines = []

    for path in sorted(root.rglob("*")):
        if any(part in BLOCKED_PARTS for part in path.parts):
            continue

        if path.name.startswith(".DS_Store"):
            continue

        depth = len(path.parts)

        if depth > max_depth:
            continue

        prefix = "  " * (depth - 1)
        marker = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{path.name}{marker}")

    return "\n".join(lines) or "No files found."


def search_files(keyword: str) -> str:
    """
    Safely search project files for a keyword.
    """

    keyword = keyword.strip()

    if not keyword:
        return "Usage: /search <keyword>"

    matches = []

    for path in sorted(Path(".").rglob("*")):
        if any(part in BLOCKED_PARTS for part in path.parts):
            continue

        if not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if keyword.lower() in text.lower():
            matches.append(str(path))

    if not matches:
        return f"No matches found for: {keyword}"

    return "\n".join(matches)
