"""
Prompt Builder for the STS AI Engine.
"""

from app.config import MAX_PROMPT_CHARS


def truncate_prompt(prompt: str) -> str:
    """
    Keep final prompts within the configured local resource budget.
    """

    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    return prompt[:MAX_PROMPT_CHARS] + "\n\n[Prompt truncated: resource budget reached.]"


def build_prompt(
    system_prompt: str,
    conversation: str,
    user_question: str,
    knowledge: str = "",
) -> str:
    """
    Build the final prompt for the LLM.
    """

    sections = [
        system_prompt.strip(),
    ]

    if knowledge.strip():
        sections.append(
            f"Knowledge Base:\n{knowledge.strip()}"
        )

    if conversation.strip():
        sections.append(
            f"Conversation History:\n{conversation.strip()}"
        )

    sections.append(
        f"User Question:\n{user_question.strip()}"
    )

    return truncate_prompt("\n\n".join(sections))
