"""
Simple tool router for the STS AI Engine.
"""

from time import perf_counter

from app.command_registry import get_handler
from app.agent_config import load_agent_definition
from app.audit_log import write_audit_record
from app.memory import ConversationMemory


def tool_allowed(agent_name: str | None, command_name: str) -> bool:
    """
    Return whether an active agent may run a registered stateless tool.
    """

    if agent_name is None:
        return True

    agent_definition = load_agent_definition(agent_name)
    return command_name in agent_definition["allowed_tools"]


def route_tool(
    command: str,
    memory: ConversationMemory,
    agent_name: str | None = None,
) -> str | None:
    """
    Route simple slash commands to internal tools.
    """

    command = command.strip()

    parts = command.split(" ", 1)
    command_name = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    handler = get_handler(command_name)
    if handler:
        started_at = perf_counter()
        if not tool_allowed(agent_name, command_name):
            agent_definition = load_agent_definition(agent_name)
            write_audit_record(
                agent_name=agent_name,
                model=agent_definition["model"],
                status="blocked",
                duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
                memory_persisted=False,
                error_category="tool_not_allowed",
            )
            return f"Tool not allowed for agent: {agent_name}"

        return handler(args)

    if command == "/memory":
        return memory.context() or "No memory saved."

    if command == "/clear":
        memory.clear()
        return "Memory cleared."

    return None
