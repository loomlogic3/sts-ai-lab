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
