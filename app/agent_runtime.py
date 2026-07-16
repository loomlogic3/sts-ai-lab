"""
Canonical execution runtime for STS AI agents.
"""

from dataclasses import dataclass

from app.agent_config import load_agent_definition
from app.config import MAX_CONVERSATION_CHARS
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.ollama_client import is_ollama_error, run_ollama
from app.prompt_builder import build_prompt
from app.response_processor import clean_response


@dataclass(frozen=True)
class AgentRuntimeOptions:
    """
    Intentional execution differences for an agent path.
    """

    memory_role: str | None = None
    knowledge_chars: int | None = None
    num_predict: int | None = None
    include_agent_config: bool = False


def execute_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    options: AgentRuntimeOptions | None = None,
) -> str:
    """
    Execute an agent through the shared local runtime.
    """

    options = options or AgentRuntimeOptions()
    agent_definition = load_agent_definition(agent_name)
    conversation = memory.context()[-MAX_CONVERSATION_CHARS:]
    knowledge = search_knowledge(question)

    if options.knowledge_chars is not None:
        knowledge = knowledge[:options.knowledge_chars]

    if options.include_agent_config:
        config_context = (
            "Agent configuration:\n"
            f"- Agent name: {agent_name}\n"
            f"- Model: {agent_definition['model']}\n"
            f"- Description: {agent_definition['description']}\n"
        )
        conversation = f"{config_context}\n{conversation}"

    prompt = build_prompt(
        system_prompt=agent_definition["prompt_text"],
        conversation=conversation,
        user_question=question,
        knowledge=knowledge,
    )

    ollama_options = {
        "temperature": agent_definition["temperature"],
    }
    if options.num_predict is not None:
        ollama_options["num_predict"] = options.num_predict

    raw_answer = run_ollama(
        agent_definition["model"],
        prompt,
        **ollama_options,
    )
    answer = clean_response(raw_answer)

    if is_ollama_error(answer):
        return answer

    memory.add("User", question)
    memory.add(options.memory_role or agent_name, answer)
    memory.save()

    return answer
