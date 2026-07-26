"""
Read-only file tools for STS AI Lab.
"""

from app.config import (
    MAX_FILE_READ_CHARS,
    MAX_SEARCH_FILE_CHARS,
    MAX_SEARCH_FILES,
    MAX_SEARCH_RESULTS,
)
from app.workspace import (
    PROTECTED_WORKSPACE_PARTS,
    Workspace,
    get_workspace,
)


BLOCKED_PARTS = PROTECTED_WORKSPACE_PARTS


def truncate_text(text: str, max_chars: int) -> str:
    """
    Limit large text blocks so local tools stay responsive.
    """

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n[Output truncated: resource budget reached.]"


def safe_project_path(
    path_text: str,
    workspace: Workspace | None = None,
):
    """
    Resolve a user path and ensure it stays inside the project root.
    """

    return get_workspace(workspace).resolve_path(path_text)


def read_file(
    path_text: str,
    workspace: Workspace | None = None,
) -> str:
    """
    Safely read a project file.
    """

    path = safe_project_path(path_text, workspace)

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


def project_tree(
    max_depth: int = 2,
    workspace: Workspace | None = None,
) -> str:
    """
    Safely list project files up to a limited depth.
    """

    active_workspace = get_workspace(workspace)
    lines = []

    for path in sorted(active_workspace.root.rglob("*")):
        relative = active_workspace.relative_path(path)
        if relative is None:
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


def search_files(
    keyword: str,
    workspace: Workspace | None = None,
) -> str:
    """
    Safely search project files for a keyword.
    """

    keyword = keyword.strip()

    if not keyword:
        return "Usage: /search <keyword>"

    active_workspace = get_workspace(workspace)
    matches = []
    scanned_files = 0

    for path in sorted(active_workspace.root.rglob("*")):
        relative = active_workspace.relative_path(path)
        if relative is None:
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


def grep_files(
    keyword: str,
    workspace: Workspace | None = None,
) -> str:
    """
    Search safe project files and return matching lines with line numbers.
    """

    keyword = keyword.strip()

    if not keyword:
        return "Usage: /grep <keyword>"

    active_workspace = get_workspace(workspace)
    matches = []
    scanned_files = 0

    for path in sorted(active_workspace.root.rglob("*")):
        relative = active_workspace.relative_path(path)
        if relative is None:
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


def find_todos(workspace: Workspace | None = None) -> str:
    """
    Find TODO/FIXME notes in safe project files.
    """

    keywords = ("TODO", "FIXME")
    active_workspace = get_workspace(workspace)
    matches = []
    scanned_files = 0

    for path in sorted(active_workspace.root.rglob("*")):
        relative = active_workspace.relative_path(path)
        if relative is None:
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
