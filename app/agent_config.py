"""
Agent configuration loader.
"""

import json
from pathlib import Path

AGENT_DIR = Path("agents")


def load_agent_config(agent_name: str) -> dict:
    """
    Load configuration for an AI agent.
    """

    path = AGENT_DIR / f"{agent_name}.json"

    if not path.exists():
        return {
            "model": "llama3.2:1b",
            "temperature": 0.2,
            "description": ""
        }

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
