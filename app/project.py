"""
Project service for STS AI Lab.
"""

from pathlib import Path

from app.agents import list_agents
from app.experiments import list_experiments
from app.memory import MEMORY_FILE
from app.tool_registry import list_tools


def project_summary() -> str:
    """
    Return a summary of the current STS AI Lab project.
    """

    knowledge_count = len(list(Path("knowledge").glob("*.md")))

    lines = [
        "STS AI Lab Project",
        "",
        f"Agents      : {len(list_agents())}",
        f"Tools       : {len(list_tools())}",
        f"Knowledge   : {knowledge_count}",
        f"Experiments : {len(list_experiments())}",
        f"Memory      : {'present' if MEMORY_FILE.exists() else 'missing'}",
    ]

    return "\n".join(lines)
