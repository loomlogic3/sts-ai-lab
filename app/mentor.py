from app.config import PROMPT_DIRECTORY
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.ollama_client import is_ollama_error, run_ollama
from app.prompt_builder import build_prompt
from app.prompt_loader import load_prompt
from app.response_processor import clean_response


def ask_mentor(question: str, memory: ConversationMemory) -> str:
    """
    Ask STS Mentor a question using conversation memory and relevant knowledge.
    """

    system_prompt = load_prompt("sts_mentor.md", PROMPT_DIRECTORY)
    # Keep mentor prompt small so identity/safety instructions are not truncated.
    conversation_context = memory.context()[-1000:]
    knowledge = search_knowledge(question)[:1200]

    full_prompt = build_prompt(
        system_prompt=system_prompt,
        conversation=conversation_context,
        user_question=question,
        knowledge=knowledge,
    )

    raw_answer = run_ollama("sts-fast", full_prompt, num_predict=80)
    answer = clean_response(raw_answer)

    if is_ollama_error(answer):
        return answer

    memory.add("User", question)
    memory.add("STS Mentor", answer)
    memory.save()

    return answer
