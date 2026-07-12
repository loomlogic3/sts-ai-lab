"""
Simple conversation memory for the STS AI Engine.
"""

import json
import re
from pathlib import Path
from typing import List


MEMORY_FILE = Path("data/memory.json")
MEMORY_DIR = Path("data/memory")
MAX_MEMORY_MESSAGES = 40


def safe_memory_name(name: str) -> str:
    """
    Convert an agent or session name into a safe memory filename stem.
    """

    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip())
    return cleaned.strip("_") or "default"


class ConversationMemory:
    def __init__(self, name: str = "default") -> None:
        self.name = safe_memory_name(name)
        self.path = MEMORY_FILE if self.name == "default" else MEMORY_DIR / f"{self.name}.json"
        self.messages: List[str] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append(f"{role}: {content}")
        self.messages = self.messages[-MAX_MEMORY_MESSAGES:]

    def context(self) -> str:
        return "\n".join(self.messages)

    def clear(self) -> None:
        self.messages.clear()
        self.save()

    def latest_user_fact(self) -> str | None:
        for message in reversed(self.messages):
            if message.startswith("User:"):
                return message.replace("User:", "").strip()

        return None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "facts": self.messages,
        }

        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

    def load(self) -> None:
        if not self.path.exists():
            return

        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            corrupt_path = self.path.with_suffix(".corrupt.json")

            try:
                self.path.replace(corrupt_path)
            except OSError:
                pass

            self.messages = []
            return

        facts = data.get("facts", [])
        if not isinstance(facts, list):
            facts = []

        self.messages = facts[-MAX_MEMORY_MESSAGES:]
