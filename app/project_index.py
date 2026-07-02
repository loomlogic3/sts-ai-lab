"""
Project index service for STS AI Lab.
"""

import ast
from pathlib import Path

from app.file_tools import BLOCKED_PARTS


def index_python_file(path: Path) -> dict:
    """
    Index imports, functions, and classes in a Python file.
    """

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (UnicodeDecodeError, SyntaxError):
        return {
            "file": str(path),
            "imports": [],
            "functions": [],
            "classes": [],
        }

    imports = []
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        if isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")

        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

        if isinstance(node, ast.ClassDef):
            classes.append(node.name)

    return {
        "file": str(path),
        "imports": sorted(set(imports)),
        "functions": sorted(set(functions)),
        "classes": sorted(set(classes)),
    }


def build_project_index() -> list[dict]:
    """
    Build an index of safe Python project files.
    """

    results = []

    for path in sorted(Path(".").rglob("*.py")):
        if any(part in BLOCKED_PARTS for part in path.parts):
            continue

        results.append(index_python_file(path))

    return results


def format_project_index() -> str:
    """
    Format the project index for display.
    """

    index = build_project_index()

    lines = ["STS AI Lab Project Index", ""]

    for item in index:
        lines.append(f"✓ {item['file']}")

        if item["classes"]:
            lines.append("  Classes:")
            for name in item["classes"]:
                lines.append(f"    - {name}")

        if item["functions"]:
            lines.append("  Functions:")
            for name in item["functions"]:
                lines.append(f"    - {name}")

        if item["imports"]:
            lines.append("  Imports:")
            for name in item["imports"]:
                lines.append(f"    - {name}")

        lines.append("")

    return "\n".join(lines)


def find_symbol(symbol: str) -> str:
    """
    Find where a symbol appears in the Python project index.
    """

    symbol = symbol.strip()

    if not symbol:
        return "Usage: /where <symbol>"

    matches = []

    for item in build_project_index():
        file_path = item["file"]

        if symbol in item["functions"]:
            matches.append(f"{symbol} function defined in {file_path}")

        if symbol in item["classes"]:
            matches.append(f"{symbol} class defined in {file_path}")

        if symbol in item["imports"]:
            matches.append(f"{symbol} imported in {file_path}")

    if not matches:
        return f"No indexed symbol found for: {symbol}"

    return "\n".join(matches)


def project_map() -> str:
    """
    Build a simple architecture map from the Python project index.
    """

    index = build_project_index()

    lines = [
        "STS AI Lab Project Map",
        "",
        "Core Modules:",
    ]

    for item in index:
        file_path = item["file"]

        if file_path in {
            "app/cli.py",
            "app/chat.py",
            "app/ai_engine.py",
            "app/tool_router.py",
            "app/tool_registry.py",
            "app/project_index.py",
            "app/code_understanding.py",
            "app/ollama_client.py",
        }:
            lines.append(f"- {file_path}")

    lines.extend([
        "",
        "Likely Flow:",
        "CLI -> Chat -> Tool Router -> Python Tools",
        "CLI -> Chat -> AI Engine -> Ollama Client",
        "",
        "Note:",
        "- This is a fast structural map generated from project files.",
    ])

    return "\n".join(lines)
