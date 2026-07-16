from app.config import (
    MAX_MENTOR_KNOWLEDGE_CHARS,
    MENTOR_NUM_PREDICT,
)
from app.agent_runtime import AgentRuntimeOptions, execute_agent
from app.memory import ConversationMemory


def ask_mentor(question: str, memory: ConversationMemory) -> str:
    """
    Ask STS Mentor a question using conversation memory and relevant knowledge.
    """

    return execute_agent(
        "sts_mentor",
        question,
        memory,
        AgentRuntimeOptions(
            memory_role="STS Mentor",
            knowledge_chars=MAX_MENTOR_KNOWLEDGE_CHARS,
            num_predict=MENTOR_NUM_PREDICT,
        ),
    )
