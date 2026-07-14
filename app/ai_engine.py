"""
Core AI Engine for STS AI Lab.
"""

from app.agent_config import load_agent_config
from app.agent_registry import load_agent_prompt
from app.config import MAX_CONVERSATION_CHARS
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.ollama_client import is_ollama_error, run_ollama
from app.prompt_builder import build_prompt
from app.response_processor import clean_response


def answer_with_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
) -> str:
    """
    Generate an answer using a selected agent.
    """

    agent_config = load_agent_config(agent_name)
    model = agent_config.get("model", "llama3.2:1b")
    temperature = agent_config.get("temperature", 0.2)

    system_prompt = load_agent_prompt(agent_name)
    conversation_context = memory.context()[-MAX_CONVERSATION_CHARS:]
    knowledge = search_knowledge(question)

    config_context = (
        f"Agent configuration:\n"
        f"- Agent name: {agent_name}\n"
        f"- Model: {model}\n"
        f"- Description: {agent_config.get('description', '')}\n"
    )

    full_prompt = build_prompt(
        system_prompt=system_prompt,
        conversation=f"{config_context}\n{conversation_context}",
        user_question=question,
        knowledge=knowledge,
    )

    raw_answer = run_ollama(model, full_prompt, temperature=temperature)
    answer = clean_response(raw_answer)

    if is_ollama_error(answer):
        return answer

    memory.add("User", question)
    memory.add(agent_name, answer)
    memory.save()

    return answer
