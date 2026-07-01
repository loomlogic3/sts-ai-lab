"""
Code understanding service for STS AI Lab.
"""

from pathlib import Path

from app.file_tools import read_file
from app.ollama_client import run_ollama


MAX_CHARS = 2500


def explain_file(path: str, model: str = "sts-fast") -> str:
    """
    Explain the purpose of a project file.
    """

    source = read_file(path)

    if source.startswith("Blocked") or source.startswith("File not found"):
        return source

    source = source[:MAX_CHARS]
    filename = Path(path).name

    prompt = f"""
You are the STS Code Agent.

Analyze this file.

File: {filename}

Explain:
- Purpose
- Main functions/classes
- Dependencies
- Role in the project
- Possible improvements, but do not rewrite code

Keep the explanation concise.

SOURCE:

{source}
"""

    return run_ollama(model, prompt)
