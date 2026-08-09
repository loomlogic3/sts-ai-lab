import ast
from pathlib import Path

import pytest

from app import model_execution
from app.ollama_client import OllamaResult


def test_model_execution_propagates_model_and_options(monkeypatch):
    captured = {}

    def fake_run_ollama_result(model, prompt, **options):
        captured["call"] = (model, prompt, options)
        return OllamaResult("answer")

    monkeypatch.setattr(
        model_execution,
        "run_ollama_result",
        fake_run_ollama_result,
    )

    result = model_execution.execute_model(
        model="canonical-model",
        prompt="private prompt",
        temperature=0.35,
        num_predict=77,
    )

    assert result.response == "answer"
    assert result.status == "success"
    assert result.error_category is None
    assert result.metrics.prompt_chars == len("private prompt")
    assert captured["call"] == (
        "canonical-model",
        "private prompt",
        {"temperature": 0.35, "num_predict": 77},
    )


def test_default_output_limit_remains_owned_by_ollama_client(monkeypatch):
    captured = {}

    def fake_run_ollama_result(model, prompt, **options):
        captured["options"] = options
        return OllamaResult("answer")

    monkeypatch.setattr(
        model_execution,
        "run_ollama_result",
        fake_run_ollama_result,
    )

    model_execution.execute_model(
        model="canonical-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert captured["options"] == {"temperature": 0.2}


def test_model_execution_exposes_privacy_safe_metrics(monkeypatch):
    monkeypatch.setattr(
        model_execution,
        "run_ollama_result",
        lambda *args, **kwargs: OllamaResult(
            response="private response",
            total_duration_ms=2170,
            load_duration_ms=400,
            prompt_eval_count=56,
            prompt_eval_duration_ms=240,
            eval_count=8,
            eval_duration_ms=1520,
            prompt_tokens_per_second=233.33,
            output_tokens_per_second=5.26,
        ),
    )

    result = model_execution.execute_model(
        model="canonical-model",
        prompt="private user prompt",
        temperature=0.2,
    )

    assert result.metrics.total_duration_ms == 2170
    assert result.metrics.load_duration_ms == 400
    assert result.metrics.prompt_eval_count == 56
    assert result.metrics.prompt_eval_duration_ms == 240
    assert result.metrics.eval_count == 8
    assert result.metrics.eval_duration_ms == 1520
    assert result.metrics.prompt_tokens_per_second == 233.33
    assert result.metrics.output_tokens_per_second == 5.26
    assert result.metrics.prompt_chars == len("private user prompt")
    serialized = repr(result.metrics)
    assert "private user prompt" not in serialized
    assert "private response" not in serialized


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
        "run_ollama_result",
        lambda *args, **kwargs: OllamaResult(response),
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
                imported_ollama_runner = (
                    node.module == "app.ollama_client"
                    and any(
                        alias.name in {"run_ollama", "run_ollama_result"}
                        for alias in node.names
                    )
                )
                if imported_ollama_runner and path.name not in approved_modules:
                    violations.append(str(path))

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"run_ollama", "run_ollama_result"}
                and path.name not in approved_modules
            ):
                violations.append(str(path))

    assert violations == []
