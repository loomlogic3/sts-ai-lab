"""
Prompt Builder for the STS AI Engine.
"""


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

    return "\n\n".join(sections)
