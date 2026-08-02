from app.config import (
    MAX_MENTOR_KNOWLEDGE_CHARS,
    MENTOR_NUM_PREDICT,
)
from app.agent_runtime import AgentRuntimeOptions, execute_agent
from app.memory import ConversationMemory
from app.runtime_status import RuntimeStatusCallback


def ask_mentor(
    question: str,
    memory: ConversationMemory,
    on_status: RuntimeStatusCallback | None = None,
) -> str:
    """
    Ask STS Mentor a question using conversation memory and relevant knowledge.
    """

    options = AgentRuntimeOptions(
        memory_role="STS Mentor",
        knowledge_chars=MAX_MENTOR_KNOWLEDGE_CHARS,
        num_predict=MENTOR_NUM_PREDICT,
    )
    if on_status is None:
        return execute_agent("sts_mentor", question, memory, options)
    return execute_agent(
        "sts_mentor",
        question,
        memory,
        options,
        on_status=on_status,
    )
