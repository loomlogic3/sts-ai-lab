"""
Tool registry for STS AI Lab.
"""


def list_tools() -> list[dict]:
    """
    Return available STS AI Lab tools.
    """

    return [
        {
            "name": "memory",
            "command": "/memory",
            "description": "Show saved memory.",
        },
        {
            "name": "clear",
            "command": "/clear",
            "description": "Clear persistent memory.",
        },
        {
            "name": "knowledge",
            "command": "/knowledge <query>",
            "description": "Search the knowledge base.",
        },
        {
            "name": "log",
            "command": "/log <note>",
            "description": "Save an experiment note.",
        },
        {
            "name": "experiments",
            "command": "/experiments",
            "description": "List experiment logs.",
        },
        {
            "name": "read",
            "command": "/read <file_path>",
            "description": "Read a project file safely.",
        },
        {
            "name": "tree",
            "command": "/tree",
            "description": "Show project structure safely.",
        },
        {
            "name": "search",
            "command": "/search <keyword>",
            "description": "Search safe project files.",
        },
        {
            "name": "grep",
            "command": "/grep <keyword>",
            "description": "Search files and show matching line numbers.",
        },
        {
            "name": "explain",
            "command": "/explain <file_path>",
            "description": "Explain a project file.",
        },
        {
            "name": "functions",
            "command": "/functions <file.py>",
            "description": "List Python functions in a file.",
        },
        {
            "name": "classes",
            "command": "/classes <file.py>",
            "description": "List Python classes in a file.",
        },
        {
            "name": "imports",
            "command": "/imports <file.py>",
            "description": "List Python imports in a file.",
        },
        {
            "name": "index",
            "command": "/index",
            "description": "Build a Python project index.",
        },
        {
            "name": "where",
            "command": "/where <symbol>",
            "description": "Find where a Python symbol is indexed.",
        },
        {
            "name": "tools",
            "command": "/tools",
            "description": "List available tools.",
        },
    ]


def format_tools() -> str:
    """
    Format available tools for display.
    """

    lines = ["Available tools:"]

    for tool in list_tools():
        lines.append(
            f"- {tool['command']}: {tool['description']}"
        )

    return "\n".join(lines)
