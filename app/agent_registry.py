"""
Agent registry for the STS AI Engine.
"""

from pathlib import Path

AGENT_DIR = Path("agents")


def list_agents() -> list[str]:
    """
    List available agent names.
    """

    if not AGENT_DIR.exists():
        return []

    return sorted(path.stem for path in AGENT_DIR.glob("*.md"))


def load_agent_prompt(agent_name: str) -> str:
    """
    Load an agent prompt by name.
    """

    path = AGENT_DIR / f"{agent_name}.md"

    if not path.exists():
        available = ", ".join(list_agents()) or "none"
        raise FileNotFoundError(
            f"Agent not found: {agent_name}. Available agents: {available}"
        )

    return path.read_text(encoding="utf-8")
