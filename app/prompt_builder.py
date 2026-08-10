"""
Prompt Builder for the STS AI Engine.
"""

from dataclasses import dataclass

from app.config import MAX_PROMPT_CHARS


@dataclass(frozen=True)
class PromptProfile:
    """Content-free measurements of one canonical prompt composition."""

    system_prompt_chars: int = 0
    conversation_chars: int = 0
    knowledge_chars: int = 0
    caller_context_chars: int = 0
    agent_context_chars: int = 0
    user_input_chars: int = 0
    untruncated_prompt_chars: int = 0
    final_prompt_chars: int = 0
    conversation_truncated: bool = False
    knowledge_truncated: bool = False
    final_prompt_truncated: bool = False


@dataclass(frozen=True)
class PromptBuildResult:
    """Canonical prompt text paired with privacy-safe composition metadata."""

    prompt: str
    profile: PromptProfile


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

    return build_prompt_result(
        system_prompt=system_prompt,
        conversation=conversation,
        user_question=user_question,
        knowledge=knowledge,
    ).prompt


def build_prompt_result(
    system_prompt: str,
    conversation: str,
    user_question: str,
    knowledge: str = "",
    *,
    caller_context: str = "",
    agent_context: str = "",
    conversation_truncated: bool = False,
    knowledge_truncated: bool = False,
) -> PromptBuildResult:
    """Build the canonical prompt once and return content-free measurements."""

    combined_conversation = conversation
    if caller_context:
        formatted_caller_context = (
            "Caller-provided context:\n"
            f"{caller_context}"
        )
        combined_conversation = (
            f"{combined_conversation}\n\n{formatted_caller_context}"
            if combined_conversation
            else formatted_caller_context
        )

    if agent_context:
        combined_conversation = f"{agent_context}\n{combined_conversation}"

    sections = [
        system_prompt.strip(),
    ]

    if knowledge.strip():
        sections.append(
            f"Knowledge Base:\n{knowledge.strip()}"
        )

    if combined_conversation.strip():
        sections.append(
            f"Conversation History:\n{combined_conversation.strip()}"
        )

    sections.append(
        f"User Question:\n{user_question.strip()}"
    )

    untruncated_prompt = "\n\n".join(sections)
    prompt = truncate_prompt(untruncated_prompt)

    return PromptBuildResult(
        prompt=prompt,
        profile=PromptProfile(
            system_prompt_chars=len(system_prompt.strip()),
            conversation_chars=len(conversation.strip()),
            knowledge_chars=len(knowledge.strip()),
            caller_context_chars=len(caller_context),
            agent_context_chars=len(agent_context.strip()),
            user_input_chars=len(user_question.strip()),
            untruncated_prompt_chars=len(untruncated_prompt),
            final_prompt_chars=len(prompt),
            conversation_truncated=conversation_truncated,
            knowledge_truncated=knowledge_truncated,
            final_prompt_truncated=len(untruncated_prompt) > MAX_PROMPT_CHARS,
        ),
    )
