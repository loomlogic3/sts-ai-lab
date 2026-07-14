"""
Simple tool router for the STS AI Engine.
"""

from app.command_registry import get_handler
from app.memory import ConversationMemory


def route_tool(command: str, memory: ConversationMemory) -> str | None:
    """
    Route simple slash commands to internal tools.
    """

    command = command.strip()

    parts = command.split(" ", 1)
    command_name = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    handler = get_handler(command_name)
    if handler:
        return handler(args)

    if command == "/memory":
        return memory.context() or "No memory saved."

    if command == "/clear":
        memory.clear()
        return "Memory cleared."

    return None
