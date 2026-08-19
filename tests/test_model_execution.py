import ast
from pathlib import Path

import pytest

from app import model_execution
from app.cloud_model_client import CloudModelResult
from app.ollama_client import OllamaResult


def _unset_cloud_env(monkeypatch):
    """Remove cloud provider env vars so tests route to Ollama."""
    monkeypatch.delenv("STS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("STS_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)


def test_model_execution_propagates_model_and_options(monkeypatch):
    _unset_cloud_env(monkeypatch)
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
    _unset_cloud_env(monkeypatch)
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
    _unset_cloud_env(monkeypatch)
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
    _unset_cloud_env(monkeypatch)
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


def test_model_execution_routes_to_openai_compatible_provider(monkeypatch):
    captured = {}
    monkeypatch.setenv("STS_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "private-key")
    monkeypatch.setenv("STS_MODEL", "gpt-test")

    def unexpected_ollama(*args, **kwargs):
        raise AssertionError("Ollama must not be called for cloud provider")

    def fake_cloud_result(**kwargs):
        captured.update(kwargs)
        return CloudModelResult("cloud answer")

    monkeypatch.setattr(model_execution, "run_ollama_result", unexpected_ollama)
    monkeypatch.setattr(
        model_execution,
        "run_cloud_model_result",
        fake_cloud_result,
    )

    result = model_execution.execute_model(
        model="local-agent-model",
        prompt="private prompt",
        temperature=0.4,
        num_predict=55,
    )

    assert result.response == "cloud answer"
    assert result.status == "success"
    assert result.provider == "openai"
    assert result.model == "gpt-test"
    assert result.metrics.prompt_chars == len("private prompt")
    assert captured["config"].provider == "openai"
    assert captured["config"].api_key == "private-key"
    assert captured["model"] == "gpt-test"
    assert captured["prompt"] == "private prompt"
    assert captured["temperature"] == 0.4
    assert captured["num_predict"] == 55


def test_missing_opencode_configuration_fails_without_network(monkeypatch):
    monkeypatch.setenv("STS_MODEL_PROVIDER", "opencode")
    monkeypatch.setenv("STS_MODEL", "opencode-hosted-model")
    monkeypatch.delenv("STS_OPENCODE_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    monkeypatch.delenv("STS_OPENCODE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENCODE_BASE_URL", raising=False)

    def unexpected_cloud(*args, **kwargs):
        raise AssertionError("cloud transport must not be called")

    monkeypatch.setattr(
        model_execution,
        "run_cloud_model_result",
        unexpected_cloud,
    )

    result = model_execution.execute_model(
        model="local-agent-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.status == "failure"
    assert result.provider == "opencode"
    assert result.model == "opencode-hosted-model"
    assert result.error_category == "cloud_provider_not_configured"
    assert "STS_OPENCODE_API_KEY" in result.response


def test_cloud_model_errors_are_classified(monkeypatch):
    monkeypatch.setenv("STS_MODEL_PROVIDER", "openai-compatible")
    monkeypatch.setenv("STS_OPENAI_API_KEY", "private-key")
    monkeypatch.setenv("STS_OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("STS_MODEL", "cloud-model")
    monkeypatch.setattr(
        model_execution,
        "run_cloud_model_result",
        lambda **kwargs: CloudModelResult(
            "Cloud model request timed out. Is the provider overloaded?"
        ),
    )

    result = model_execution.execute_model(
        model="local-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.status == "timeout"
    assert result.error_category == "cloud_timeout"
    assert result.provider == "openai-compatible"
    assert result.model == "cloud-model"


def test_unknown_provider_falls_back_to_ollama(monkeypatch):
    _unset_cloud_env(monkeypatch)
    captured = {}
    monkeypatch.setenv("STS_MODEL_PROVIDER", "unknown-provider")

    def fake_run_ollama_result(model, prompt, **options):
        captured["model"] = model
        return OllamaResult("answer")

    monkeypatch.setattr(
        model_execution,
        "run_ollama_result",
        fake_run_ollama_result,
    )

    result = model_execution.execute_model(
        model="local-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.status == "success"
    assert result.provider == "ollama"
    assert captured["model"] == "local-model"


def test_google_ai_studio_routes_to_cloud(monkeypatch):
    captured = {}
    monkeypatch.setenv("STS_MODEL_PROVIDER", "google-ai-studio")
    monkeypatch.setenv("GEMINI_API_KEY", "private-gemini-key")
    monkeypatch.setenv("STS_MODEL", "gemini-2.5-flash")

    def unexpected_ollama(*args, **kwargs):
        raise AssertionError("Ollama must not be called for Google AI Studio")

    def fake_cloud_result(**kwargs):
        captured.update(kwargs)
        return CloudModelResult("gemini answer")

    monkeypatch.setattr(model_execution, "run_ollama_result", unexpected_ollama)
    monkeypatch.setattr(
        model_execution, "run_cloud_model_result", fake_cloud_result,
    )

    result = model_execution.execute_model(
        model="local-model",
        prompt="prompt",
        temperature=0.3,
    )

    assert result.response == "gemini answer"
    assert result.status == "success"
    assert result.provider == "google-ai-studio"
    assert result.model == "gemini-2.5-flash"
    assert captured["config"].base_url == (
        "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    assert captured["config"].api_key == "private-gemini-key"


def test_gemini_alias_resolves_to_google_ai_studio(monkeypatch):
    monkeypatch.setenv("STS_MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "private-gemini-key")
    monkeypatch.setenv("STS_MODEL", "gemini-2.5-flash")

    monkeypatch.setattr(
        model_execution,
        "run_cloud_model_result",
        lambda **kwargs: CloudModelResult("answer"),
    )

    result = model_execution.execute_model(
        model="local-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.provider == "google-ai-studio"
    assert result.status == "success"


def test_missing_google_ai_studio_configuration_fails_without_network(
    monkeypatch,
):
    monkeypatch.setenv("STS_MODEL_PROVIDER", "google-ai-studio")
    monkeypatch.setenv("STS_MODEL", "gemini-2.5-flash")
    monkeypatch.delenv("STS_GOOGLE_AI_STUDIO_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def unexpected_cloud(*args, **kwargs):
        raise AssertionError("cloud transport must not be called")

    monkeypatch.setattr(
        model_execution, "run_cloud_model_result", unexpected_cloud,
    )

    result = model_execution.execute_model(
        model="local-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.status == "failure"
    assert result.provider == "google-ai-studio"
    assert result.model == "gemini-2.5-flash"
    assert result.error_category == "cloud_provider_not_configured"
    assert "GEMINI_API_KEY" in result.response


def test_opencode_uses_zen_default_base_url(monkeypatch):
    captured = {}
    monkeypatch.setenv("STS_MODEL_PROVIDER", "opencode")
    monkeypatch.setenv("OPENCODE_API_KEY", "private-key")
    monkeypatch.delenv("STS_OPENCODE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENCODE_BASE_URL", raising=False)
    monkeypatch.setenv("STS_MODEL", "big-pickle")

    def fake_cloud_result(**kwargs):
        captured.update(kwargs)
        return CloudModelResult("opencode answer")

    monkeypatch.setattr(
        model_execution, "run_cloud_model_result", fake_cloud_result,
    )

    result = model_execution.execute_model(
        model="local-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.response == "opencode answer"
    assert result.status == "success"
    assert result.provider == "opencode"
    assert captured["config"].base_url == "https://opencode.ai/zen/v1"


def test_sts_model_env_overrides_configured_model(monkeypatch):
    _unset_cloud_env(monkeypatch)
    captured = {}
    monkeypatch.setenv("STS_MODEL", "env-override-model")

    def fake_run_ollama_result(model, prompt, **options):
        captured["model"] = model
        return OllamaResult("answer")

    monkeypatch.setattr(
        model_execution,
        "run_ollama_result",
        fake_run_ollama_result,
    )

    result = model_execution.execute_model(
        model="agent-config-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.model == "env-override-model"
    assert captured["model"] == "env-override-model"


def test_without_sts_model_configured_model_is_used(monkeypatch):
    _unset_cloud_env(monkeypatch)
    captured = {}
    monkeypatch.delenv("STS_MODEL", raising=False)

    def fake_run_ollama_result(model, prompt, **options):
        captured["model"] = model
        return OllamaResult("answer")

    monkeypatch.setattr(
        model_execution,
        "run_ollama_result",
        fake_run_ollama_result,
    )

    result = model_execution.execute_model(
        model="agent-config-model",
        prompt="prompt",
        temperature=0.2,
    )

    assert result.model == "agent-config-model"
    assert captured["model"] == "agent-config-model"


def test_raw_cloud_client_usage_is_limited_to_approved_modules():
    approved_modules = {
        "model_execution.py",
    }
    violations = []

    for path in sorted(Path("app").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_cloud_client = (
                    node.module == "app.cloud_model_client"
                    and any(
                        alias.name
                        in {
                            "CloudModelConfig",
                            "CloudModelResult",
                            "is_cloud_model_error",
                            "run_cloud_model_result",
                        }
                        for alias in node.names
                    )
                )
                if imported_cloud_client and path.name not in approved_modules:
                    violations.append(str(path))

    assert violations == []


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
