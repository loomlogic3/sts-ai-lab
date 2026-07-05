"""
Command handlers for STS AI Lab.
"""

from app.file_tools import project_tree
from app.tool_registry import format_tools


def tools_handler(args: str) -> str:
    """
    Handle the /tools command.
    """
    return format_tools()


def tree_handler(args: str) -> str:
    """
    Handle the /tree command.
    """
    return project_tree()
