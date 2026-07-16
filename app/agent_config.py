"""
Agent configuration loader.
"""

import json
from pathlib import Path

AGENT_DIR = Path("agents")
DEFAULT_AGENT_MODEL = "llama3.2:1b"
DEFAULT_AGENT_TEMPERATURE = 0.2
DEFAULT_AGENT_DESCRIPTION = ""
DEFAULT_ALLOWED_TOOLS: tuple[str, ...] = ()


def agent_prompt_path(agent_name: str, prompt_file: str | None = None) -> Path:
    """
    Return the prompt path for an agent definition.
    """

    return AGENT_DIR / (prompt_file or f"{agent_name}.md")


def load_agent_config(agent_name: str) -> dict:
    """
    Load configuration for an AI agent.
    """

    path = AGENT_DIR / f"{agent_name}.json"

    if not path.exists():
        return {
            "prompt": f"{agent_name}.md",
            "model": DEFAULT_AGENT_MODEL,
            "temperature": DEFAULT_AGENT_TEMPERATURE,
            "description": DEFAULT_AGENT_DESCRIPTION,
            "allowed_tools": DEFAULT_ALLOWED_TOOLS,
        }

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_agent_definition(agent_name: str) -> dict:
    """
    Load the canonical agent definition.

    The JSON file remains the source for model, temperature, description,
    and prompt filename. The prompt text is loaded from the referenced
    Markdown file so existing prompt files and behavior are preserved.
    """

    config = load_agent_config(agent_name)
    prompt_file = config.get("prompt", f"{agent_name}.md")
    prompt_path = agent_prompt_path(agent_name, prompt_file)

    if not prompt_path.exists():
        available = ", ".join(list_agent_names()) or "none"
        raise FileNotFoundError(
            f"Agent not found: {agent_name}. Available agents: {available}"
        )

    return {
        "name": agent_name,
        "prompt": prompt_file,
        "prompt_path": prompt_path,
        "prompt_text": prompt_path.read_text(encoding="utf-8"),
        "model": config.get("model", DEFAULT_AGENT_MODEL),
        "temperature": config.get("temperature", DEFAULT_AGENT_TEMPERATURE),
        "description": config.get("description", DEFAULT_AGENT_DESCRIPTION),
        "allowed_tools": list(config.get("allowed_tools", DEFAULT_ALLOWED_TOOLS)),
    }


def list_agent_names() -> list[str]:
    """
    List agents that have canonical JSON definitions.
    """

    if not AGENT_DIR.exists():
        return []

    return sorted(path.stem for path in AGENT_DIR.glob("*.json"))


def list_agent_definitions() -> list[dict]:
    """
    Return canonical definitions for all configured agents.
    """

    return [
        load_agent_definition(agent_name)
        for agent_name in list_agent_names()
    ]
