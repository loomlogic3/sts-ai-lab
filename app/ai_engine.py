"""
Core AI Engine for STS AI Lab.
"""

from app.agent_runtime import AgentRuntimeOptions, execute_agent
from app.memory import ConversationMemory


def answer_with_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
) -> str:
    """
    Generate an answer using a selected agent.
    """

    return execute_agent(
        agent_name,
        question,
        memory,
        AgentRuntimeOptions(include_agent_config=True),
    )
