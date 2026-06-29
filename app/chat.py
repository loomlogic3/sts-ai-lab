"""
Generic chat runner for all STS AI agents.
"""

from app.agent_registry import list_agents
from app.memory import ConversationMemory


def start_chat(agent_name: str) -> None:
    """
    Start an interactive chat session with the selected agent.
    """

    if agent_name not in list_agents():
        print(f"Unknown agent: {agent_name}")
        print()
        print("Available agents:")

        for agent in list_agents():
            print(f" - {agent}")

        return

    memory = ConversationMemory()
    memory.load()

    print(f"{agent_name} chat started.")
    print("Type /bye to exit.")
    print()
