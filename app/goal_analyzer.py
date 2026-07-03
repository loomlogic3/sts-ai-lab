"""
Simple goal analyzer for STS AI Lab.

Maps user goals to likely project modules.
"""

from app.project_index import build_project_index


KEYWORDS = {
    "cli": ["app/cli.py"],
    "chat": ["app/chat.py"],
    "memory": ["app/memory.py"],
    "knowledge": [
        "app/knowledge_loader.py",
        "app/knowledge_search.py",
    ],
    "agent": [
        "app/agent_config.py",
        "app/agent_registry.py",
        "app/agents.py",
    ],
    "tool": [
        "app/tool_router.py",
        "app/tool_registry.py",
        "app/file_tools.py",
    ],
    "model": [
        "app/models.py",
        "app/ollama_client.py",
    ],
    "project": [
        "app/project.py",
        "app/project_index.py",
    ],
}


def relevant_files(goal: str) -> list[str]:
    """
    Return files likely related to a goal.
    """

    goal = goal.lower()
    matches = []

    for keyword, files in KEYWORDS.items():
        if keyword in goal:
            matches.extend(files)

    indexed = {item["file"] for item in build_project_index()}

    return sorted(
        file
        for file in set(matches)
        if file in indexed
    )
