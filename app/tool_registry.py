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
