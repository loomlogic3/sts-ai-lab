"""
Agent management for STS AI Lab.
"""

import json
from pathlib import Path


AGENTS_DIR = Path("agents")


def list_agents() -> list[dict]:
    """
    Return information about all configured agents.
    """

    agents = []

    for path in sorted(AGENTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())

        agents.append(
            {
                "name": path.stem,
                "model": data.get("model", "unknown"),
                "description": data.get("description", ""),
            }
        )

    return agents


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
