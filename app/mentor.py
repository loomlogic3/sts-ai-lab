from app.config import DEFAULT_MODEL, PROMPT_DIRECTORY
from app.memory import ConversationMemory
from app.ollama_client import run_ollama
from app.prompt_loader import load_prompt
from app.prompt_builder import build_prompt
from app.response_processor import clean_response


def ask_mentor(question: str, memory: ConversationMemory) -> str:
    """
    Ask STS Mentor a question using conversation memory.
    """

    system_prompt = load_prompt("sts_mentor.md", PROMPT_DIRECTORY)
    conversation_context = memory.context()

    full_prompt = build_prompt(
    system_prompt=system_prompt,
    conversation=conversation_context,
    user_question=question,
)

    raw_answer = run_ollama(DEFAULT_MODEL, full_prompt)
    answer = clean_response(raw_answer)

    memory.add("User", question)
    memory.add("STS Mentor", answer)

    return answer
