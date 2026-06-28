from app.config import DEFAULT_MODEL, PROMPT_DIRECTORY
from app.ollama_client import run_ollama
from app.prompt_loader import load_prompt


def ask_mentor(question: str) -> str:
    """
    Ask STS Mentor a question.
    """

    system_prompt = load_prompt("sts_mentor.md", PROMPT_DIRECTORY)

    full_prompt = f"""{system_prompt}

User question:
{question}
"""

    return run_ollama(DEFAULT_MODEL, full_prompt)
