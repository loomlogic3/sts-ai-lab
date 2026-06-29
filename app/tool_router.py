"""
Simple tool router for the STS AI Engine.
"""

from app.experiment_logger import log_experiment
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory


def route_tool(command: str, memory: ConversationMemory) -> str | None:
    """
    Route simple slash commands to internal tools.
    """

    command = command.strip()

    if command == "/memory":
        return memory.context() or "No memory saved."

    if command == "/clear":
        memory.clear()
        return "Memory cleared."

    if command.startswith("/knowledge "):
        query = command.replace("/knowledge ", "", 1).strip()
        return search_knowledge(query) or "No knowledge found."

    if command.startswith("/log "):
        note = command.replace("/log ", "", 1).strip()

        if not note:
            return "Usage: /log <experiment note>"

        path = log_experiment("mentor_session_note", note)
        return f"Experiment saved: {path}"

    return None
