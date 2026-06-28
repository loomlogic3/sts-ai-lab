"""
Simple keyword knowledge search for the STS AI Engine.
"""

from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge")


def search_knowledge(query: str) -> str:
    """
    Return only the most relevant knowledge documents.
    """

    if not KNOWLEDGE_DIR.exists():
        return ""

    query_words = {
        word.lower()
        for word in query.split()
        if len(word) > 2
    }

    matches = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")

        score = 0

        for word in query_words:
            score += text.lower().count(word)

        if score > 0:
            matches.append((score, path.name, text))

    matches.sort(reverse=True)

    if not matches:
        return ""

    sections = []

    for score, filename, text in matches[:3]:
        sections.append(
            f"Source: {filename}\n\n{text}"
        )

    return "\n\n---\n\n".join(sections)
