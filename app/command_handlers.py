"""
Command handlers for STS AI Lab.
"""

from app.tool_registry import format_tools


def tools_handler(args: str) -> str:
    """
    Handle the /tools command.
    """
    return format_tools()
