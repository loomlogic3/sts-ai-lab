import ast
from pathlib import Path

import pytest

from app import model_execution


def test_model_execution_propagates_model_and_options(monkeypatch):
    captured = {}

    def fake_run_ollama(model, prompt, **options):
        captured["call"] = (model, prompt, options)
        return "answer"

    monkeypatch.setattr(model_execution, "run_ollama", fake_run_ollama)

    result = model_execution.execute_model(
        model="canonical-model",
        prompt="private prompt",
        temperature=0.35,
        num_predict=77,
    )

    assert result.response == "answer"
    assert result.status == "success"
    assert result.error_category is None
    assert captured["call"] == (
        "canonical-model",
        "private prompt",
        {"temperature": 0.35, "num_predict": 77},
    )


def test_default_output_limit_remains_owned_by_ollama_client(monkeypatch):
    captured = {}

    def fake_run_ollama(model, prompt, **options):
        captured["options"] = options
        return "answer"

    monkeypatch.setattr(model_execution, "run_ollama", fake_run_ollama)

    model_execution.execute_model(
        model="canonical-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert captured["options"] == {"temperature": 0.2}


@pytest.mark.parametrize(
    ("response", "status", "error_category"),
    [
        (
            "Ollama request timed out. Is the local model overloaded?",
            "timeout",
            "ollama_timeout",
        ),
        (
            "Ollama connection failed: refused",
            "failure",
            "ollama_error",
        ),
        (
            "Ollama returned an invalid JSON response.",
            "failure",
            "ollama_error",
        ),
    ],
)
def test_model_execution_classifies_existing_ollama_outcomes(
    monkeypatch,
    response,
    status,
    error_category,
):
    monkeypatch.setattr(
        model_execution,
        "run_ollama",
        lambda *args, **kwargs: response,
    )

    result = model_execution.execute_model(
        model="canonical-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.response == response
    assert result.status == status
    assert result.error_category == error_category


def test_raw_ollama_usage_is_limited_to_approved_modules():
    approved_modules = {
        "ollama_client.py",
        "model_execution.py",
    }
    violations = []

    for path in sorted(Path("app").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_run_ollama = (
                    node.module == "app.ollama_client"
                    and any(alias.name == "run_ollama" for alias in node.names)
                )
                if imported_run_ollama and path.name not in approved_modules:
                    violations.append(str(path))

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "run_ollama"
                and path.name not in approved_modules
            ):
                violations.append(str(path))

    assert violations == []
