"""
Agent management for STS AI Lab.
"""

from app.agent_config import list_agent_definitions


def list_agents() -> list[dict]:
    """
    Return information about all configured agents.
    """

    return [
        {
            "name": definition["name"],
            "model": definition["model"],
            "description": definition["description"],
        }
        for definition in list_agent_definitions()
    ]


def print_agents() -> None:
    """
    Display configured agents.
    """

    print("STS AI Lab Agents")
    print()

    for agent in list_agents():
        print(f"✓ {agent['name']}")
        print(f"  Model: {agent['model']}")
        print(f"  Role : {agent['description']}")
        print()
