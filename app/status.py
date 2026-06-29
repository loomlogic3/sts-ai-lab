"""
STS AI Lab status helper.
"""

from pathlib import Path

from app.config import DEFAULT_MODEL
from app.memory import MEMORY_FILE


def lab_status() -> str:
    """
    Return a simple status summary for the local AI Lab.
    """

    knowledge_count = len(list(Path("knowledge").glob("*.md"))) if Path("knowledge").exists() else 0
    experiment_count = len(list(Path("experiments").glob("*.md"))) if Path("experiments").exists() else 0
    memory_exists = MEMORY_FILE.exists()

    return (
        "STS AI Lab Status\n"
        f"- Default model: {DEFAULT_MODEL}\n"
        f"- Knowledge documents: {knowledge_count}\n"
        f"- Experiment logs: {experiment_count}\n"
        f"- Persistent memory file: {'present' if memory_exists else 'missing'}"
    )
