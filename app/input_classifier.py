"""
Input classifier for the STS AI Engine.
"""

from enum import Enum


class InputType(Enum):
    STATEMENT = "statement"
    AI_REQUEST = "ai_request"


REQUEST_PREFIXES = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "explain",
    "describe",
    "compare",
    "write",
    "create",
    "generate",
    "suggest",
    "show",
    "list",
    "summarize",
    "analyse",
    "analyze",
    "help",
)


def classify(text: str) -> InputType:
    """
    Decide whether the input should be remembered
    or answered by the AI.
    """

    cleaned = text.strip().lower()

    if cleaned.startswith("/"):
        return InputType.AI_REQUEST

    for prefix in REQUEST_PREFIXES:
        if cleaned.startswith(prefix):
            return InputType.AI_REQUEST

    if cleaned.endswith("?"):
        return InputType.AI_REQUEST

    return InputType.STATEMENT
