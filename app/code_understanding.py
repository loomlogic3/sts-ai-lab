"""
Code understanding service for STS AI Lab.
"""

import ast
from pathlib import Path

from app.file_tools import read_file
from app.ollama_client import run_ollama


MAX_CHARS = 2500


def explain_python_file(path: str) -> str:
    """
    Explain a Python file using Python's AST instead of the LLM.
    """

    source = read_file(path)

    if source.startswith("Blocked") or source.startswith("File not found"):
        return source

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return f"Could not parse Python file: {error}"

    imports = []
    functions = []
    classes = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)

        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

        if isinstance(node, ast.ClassDef):
            classes.append(node.name)

    lines = [
        f"File: {path}",
        "",
        "Purpose:",
        "- Python module in the STS AI Lab project.",
        "",
        "Imports:",
    ]

    lines.extend(f"- {item}" for item in imports) if imports else lines.append("- None found")

    lines.append("")
    lines.append("Functions:")
    lines.extend(f"- {item}" for item in functions) if functions else lines.append("- None found")

    lines.append("")
    lines.append("Classes:")
    lines.extend(f"- {item}" for item in classes) if classes else lines.append("- None found")

    lines.append("")
    lines.append("Note:")
    lines.append("- This is a fast structural explanation. Use deeper LLM review later if needed.")

    return "\n".join(lines)


def explain_file(path: str, model: str = "sts-fast") -> str:
    """
    Explain the purpose of a project file.
    """

    if path.endswith(".py"):
        return explain_python_file(path)

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
- Main sections
- Role in the project
- Possible improvements, but do not rewrite code

Keep the explanation concise.

SOURCE:

{source}
"""

    return run_ollama(model, prompt)
