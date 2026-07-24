"""
Code understanding service for STS AI Lab.
"""

import ast
from pathlib import Path
from time import perf_counter

from app.agent_config import load_agent_definition
from app.audit_log import write_audit_record
from app.config import MAX_CODE_EXPLANATION_CHARS
from app.file_tools import read_file
from app.model_execution import execute_model


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


def explain_file(path: str, model: str | None = None) -> str:
    """
    Explain the purpose of a project file.

    The model argument is retained for call compatibility. Canonical Code Agent
    configuration remains authoritative for model-backed explanations.
    """

    if path.endswith(".py"):
        return explain_python_file(path)

    source = read_file(path)

    if source.startswith("Blocked") or source.startswith("File not found"):
        return source

    source = source[:MAX_CODE_EXPLANATION_CHARS]
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

    agent_definition = load_agent_definition("code_agent")
    started_at = perf_counter()

    try:
        result = execute_model(
            model=agent_definition["model"],
            prompt=prompt,
            temperature=agent_definition["temperature"],
        )
    except Exception:
        write_audit_record(
            agent_name="code_agent",
            model=agent_definition["model"],
            status="failure",
            duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
            memory_persisted=False,
            error_category="runtime_error",
        )
        raise

    write_audit_record(
        agent_name="code_agent",
        model=agent_definition["model"],
        status=result.status,
        duration_ms=result.duration_ms,
        memory_persisted=False,
        error_category=result.error_category,
    )
    return result.response


def list_python_functions(path: str) -> str:
    """
    List functions in a Python file.
    """

    source = read_file(path)

    if source.startswith("Blocked") or source.startswith("File not found"):
        return source

    if not path.endswith(".py"):
        return "This tool only supports Python files."

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return f"Could not parse Python file: {error}"

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    if not functions:
        return "No functions found."

    return "\n".join(f"- {name}" for name in sorted(functions))


def list_python_imports(path: str) -> str:
    """
    List imports in a Python file.
    """

    source = read_file(path)

    if source.startswith("Blocked") or source.startswith("File not found"):
        return source

    if not path.endswith(".py"):
        return "This tool only supports Python files."

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return f"Could not parse Python file: {error}"

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        if isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")

    if not imports:
        return "No imports found."

    return "\n".join(f"- {name}" for name in sorted(set(imports)))


def list_python_classes(path: str) -> str:
    """
    List classes in a Python file.
    """

    source = read_file(path)

    if source.startswith("Blocked") or source.startswith("File not found"):
        return source

    if not path.endswith(".py"):
        return "This tool only supports Python files."

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return f"Could not parse Python file: {error}"

    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)

    if not classes:
        return "No classes found."

    return "\n".join(f"- {name}" for name in sorted(classes))


def analyze_python_file(path: str) -> str:
    """
    Produce a fast analysis report for a Python file.
    """

    lines = [
        f"Analysis: {path}",
        "",
        "Imports:",
        list_python_imports(path),
        "",
        "Classes:",
        list_python_classes(path),
        "",
        "Functions:",
        list_python_functions(path),
        "",
        "Explanation:",
        explain_file(path),
    ]

    return "\n".join(lines)
