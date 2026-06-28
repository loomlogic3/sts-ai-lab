"""
Knowledge loader for the STS AI Engine.
"""

from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge")


def load_knowledge() -> str:
    """
    Load all Markdown knowledge files into one text block.
    """

    if not KNOWLEDGE_DIR.exists():
        return ""

    documents = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        documents.append(
            f"Source: {path.name}\n\n{path.read_text(encoding='utf-8')}"
        )

    return "\n\n---\n\n".join(documents)
