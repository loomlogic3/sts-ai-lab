"""
Read-only file tools for STS AI Lab.
"""

from pathlib import Path

from app.config import (
    MAX_FILE_READ_CHARS,
    MAX_SEARCH_FILE_CHARS,
    MAX_SEARCH_FILES,
    MAX_SEARCH_RESULTS,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

BLOCKED_PARTS = {
    ".env",
    ".git",
    "__pycache__",
    "data",
}


def truncate_text(text: str, max_chars: int) -> str:
    """
    Limit large text blocks so local tools stay responsive.
    """

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n[Output truncated: resource budget reached.]"


def safe_project_path(path_text: str) -> Path | None:
    """
    Resolve a user path and ensure it stays inside the project root.
    """

    raw_path = Path(path_text).expanduser()

    if raw_path.is_absolute():
        return None

    if ".." in raw_path.parts:
        return None

    candidate = (PROJECT_ROOT / raw_path).resolve()

    if not candidate.is_relative_to(PROJECT_ROOT):
        return None

    if any(part in BLOCKED_PARTS for part in candidate.relative_to(PROJECT_ROOT).parts):
        return None

    return candidate


def read_file(path_text: str) -> str:
    """
    Safely read a project file.
    """

    path = safe_project_path(path_text)

    if path is None:
        return "Blocked: this path is not allowed."

    if not path.exists():
        return f"File not found: {path_text}"

    if not path.is_file():
        return f"Not a file: {path_text}"

    return truncate_text(
        path.read_text(encoding="utf-8"),
        MAX_FILE_READ_CHARS,
    )


def project_tree(max_depth: int = 2) -> str:
    """
    Safely list project files up to a limited depth.
    """

    lines = []

    for path in sorted(PROJECT_ROOT.rglob("*")):
        relative = path.relative_to(PROJECT_ROOT)

        if any(part in BLOCKED_PARTS for part in relative.parts):
            continue

        if path.name.startswith(".DS_Store"):
            continue

        depth = len(relative.parts)

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
    scanned_files = 0

    for path in sorted(PROJECT_ROOT.rglob("*")):
        relative = path.relative_to(PROJECT_ROOT)

        if any(part in BLOCKED_PARTS for part in relative.parts):
            continue

        if not path.is_file():
            continue

        scanned_files += 1

        if scanned_files > MAX_SEARCH_FILES:
            break

        try:
            text = path.read_text(encoding="utf-8")[:MAX_SEARCH_FILE_CHARS]
        except UnicodeDecodeError:
            continue

        if keyword.lower() in text.lower():
            matches.append(str(relative))

        if len(matches) >= MAX_SEARCH_RESULTS:
            break

    if not matches:
        return f"No matches found for: {keyword}"

    result = "\n".join(matches)

    if scanned_files > MAX_SEARCH_FILES or len(matches) >= MAX_SEARCH_RESULTS:
        result += "\n[Output limited: resource budget reached.]"

    return result


def grep_files(keyword: str) -> str:
    """
    Search safe project files and return matching lines with line numbers.
    """

    keyword = keyword.strip()

    if not keyword:
        return "Usage: /grep <keyword>"

    matches = []
    scanned_files = 0

    for path in sorted(PROJECT_ROOT.rglob("*")):
        relative = path.relative_to(PROJECT_ROOT)

        if any(part in BLOCKED_PARTS for part in relative.parts):
            continue

        if not path.is_file():
            continue

        scanned_files += 1

        if scanned_files > MAX_SEARCH_FILES:
            break

        try:
            lines = path.read_text(encoding="utf-8")[:MAX_SEARCH_FILE_CHARS].splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if keyword.lower() in line.lower():
                matches.append(f"{relative}:{line_number}: {line.strip()}")

            if len(matches) >= MAX_SEARCH_RESULTS:
                break

        if len(matches) >= MAX_SEARCH_RESULTS:
            break

    if not matches:
        return f"No matches found for: {keyword}"

    result = "\n".join(matches)

    if scanned_files > MAX_SEARCH_FILES or len(matches) >= MAX_SEARCH_RESULTS:
        result += "\n[Output limited: resource budget reached.]"

    return result


def find_todos() -> str:
    """
    Find TODO/FIXME notes in safe project files.
    """

    keywords = ("TODO", "FIXME")
    matches = []
    scanned_files = 0

    for path in sorted(PROJECT_ROOT.rglob("*")):
        relative = path.relative_to(PROJECT_ROOT)

        if any(part in BLOCKED_PARTS for part in relative.parts):
            continue

        if not path.is_file():
            continue

        scanned_files += 1

        if scanned_files > MAX_SEARCH_FILES:
            break

        try:
            lines = path.read_text(encoding="utf-8")[:MAX_SEARCH_FILE_CHARS].splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            line_lower = line.lower()

            if "find_todos" in line_lower or "todo/fixme" in line_lower:
                continue

            if any(keyword.lower() in line_lower for keyword in keywords):
                matches.append(f"{relative}:{line_number}: {line.strip()}")

            if len(matches) >= MAX_SEARCH_RESULTS:
                break

        if len(matches) >= MAX_SEARCH_RESULTS:
            break

    if not matches:
        return "No TODO/FIXME notes found."

    result = "\n".join(matches)

    if scanned_files > MAX_SEARCH_FILES or len(matches) >= MAX_SEARCH_RESULTS:
        result += "\n[Output limited: resource budget reached.]"

    return result
