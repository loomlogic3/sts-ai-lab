"""
Simple tool router for the STS AI Engine.
"""

from app.experiment_logger import log_experiment
from app.code_understanding import explain_file, list_python_functions
from app.experiments import list_experiments
from app.file_tools import grep_files, project_tree, read_file, search_files
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.tool_registry import format_tools


def route_tool(command: str, memory: ConversationMemory) -> str | None:
    """
    Route simple slash commands to internal tools.
    """

    command = command.strip()

    if command == "/tools":
        return format_tools()

    if command == "/memory":
        return memory.context() or "No memory saved."

    if command == "/clear":
        memory.clear()
        return "Memory cleared."

    if command == "/tree":
        return project_tree()

    if command.startswith("/search "):
        keyword = command.replace("/search ", "", 1).strip()
        return search_files(keyword)

    if command.startswith("/grep "):
        keyword = command.replace("/grep ", "", 1).strip()
        return grep_files(keyword)

    if command.startswith("/read "):
        file_path = command.replace("/read ", "", 1).strip()
        return read_file(file_path)

    if command.startswith("/explain "):
        file_path = command.replace("/explain ", "", 1).strip()
        return explain_file(file_path)

    if command.startswith("/functions "):
        file_path = command.replace("/functions ", "", 1).strip()
        return list_python_functions(file_path)

    if command == "/experiments":
        experiments = list_experiments()
        if not experiments:
            return "No experiments found."
        return "\n".join(path.name for path in experiments)

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
