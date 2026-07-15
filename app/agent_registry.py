"""
Agent registry for the STS AI Engine.
"""

from app.agent_config import load_agent_definition, list_agent_names


def list_agents() -> list[str]:
    """
    List available agent names.
    """

    return list_agent_names()


def load_agent_prompt(agent_name: str) -> str:
    """
    Load an agent prompt by name.
    """

    return load_agent_definition(agent_name)["prompt_text"]
