"""
Input classification for the STS AI Engine.
"""

from enum import Enum


class InputType(Enum):
    QUESTION = "question"
    STATEMENT = "statement"
    COMMAND = "command"


def classify(text: str) -> InputType:
    """
    Classify basic user input.
    """

    text = text.strip()

    if text.startswith("/"):
        return InputType.COMMAND

    if text.endswith("?"):
        return InputType.QUESTION

    return InputType.STATEMENT
