"""
Core AI Engine for STS AI Lab.
"""

from app.agent_runtime import AgentRuntimeOptions, execute_agent
from app.memory import ConversationMemory
from app.runtime_status import RuntimeStatusCallback


def answer_with_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    on_status: RuntimeStatusCallback | None = None,
) -> str:
    """
    Generate an answer using a selected agent.
    """

    options = AgentRuntimeOptions(include_agent_config=True)
    if on_status is None:
        return execute_agent(agent_name, question, memory, options)
    return execute_agent(
        agent_name,
        question,
        memory,
        options,
        on_status=on_status,
    )
