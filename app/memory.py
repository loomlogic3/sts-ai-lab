"""
Simple conversation memory for the STS AI Engine.
"""

import json
from pathlib import Path
from typing import List


MEMORY_FILE = Path("data/memory.json")


class ConversationMemory:
    def __init__(self) -> None:
        self.messages: List[str] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append(f"{role}: {content}")

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
        MEMORY_FILE.parent.mkdir(exist_ok=True)

        data = {
            "facts": self.messages,
        }

        MEMORY_FILE.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not MEMORY_FILE.exists():
            return

        data = json.loads(
            MEMORY_FILE.read_text(encoding="utf-8")
        )

        self.messages = data.get("facts", [])
