"""
Canonical governed boundary for production Python model execution.
"""

from dataclasses import dataclass
import os
from time import perf_counter
from typing import Literal

from app.cloud_model_client import (
    CloudModelConfig,
    is_cloud_model_error,
    run_cloud_model_result,
)
from app.ollama_client import is_ollama_error, run_ollama_result


ModelExecutionStatus = Literal["success", "timeout", "failure"]
ModelProvider = Literal[
    "ollama", "openai", "openai-compatible", "opencode", "google-ai-studio"
]


@dataclass(frozen=True)
class ModelExecutionMetrics:
    """Privacy-safe measurements for one local model invocation."""

    total_duration_ms: int = 0
    load_duration_ms: int = 0
    prompt_eval_count: int = 0
    prompt_eval_duration_ms: int = 0
    eval_count: int = 0
    eval_duration_ms: int = 0
    prompt_tokens_per_second: float = 0.0
    output_tokens_per_second: float = 0.0
    prompt_chars: int = 0


@dataclass(frozen=True)
class ModelExecutionResult:
    """
    Content and metadata returned by one governed model invocation.
    """

    response: str
    status: ModelExecutionStatus
    duration_ms: int
    error_category: str | None = None
    metrics: ModelExecutionMetrics = ModelExecutionMetrics()
    provider: str = "ollama"
    model: str | None = None


def execute_model(
    *,
    model: str,
    prompt: str,
    temperature: float,
    num_predict: int | None = None,
) -> ModelExecutionResult:
    """
    Invoke the configured model provider and classify its deterministic outcome.
    """

    started_at = perf_counter()
    provider = get_model_provider()
    effective_model = resolve_model_name(model)

    if provider == "ollama":
        return _execute_ollama_model(
            model=effective_model,
            prompt=prompt,
            temperature=temperature,
            num_predict=num_predict,
            started_at=started_at,
        )

    cloud_config = get_cloud_model_config(provider)
    if cloud_config is None:
        return _failure_result(
            response=_missing_cloud_configuration_message(provider),
            error_category="cloud_provider_not_configured",
            provider=provider,
            model=effective_model,
            prompt=prompt,
            started_at=started_at,
        )

    cloud_result = run_cloud_model_result(
        config=cloud_config,
        model=effective_model,
        prompt=prompt,
        temperature=temperature,
        num_predict=num_predict,
    )

    if cloud_result.response.startswith("Cloud model request timed out."):
        status = "timeout"
        error_category = "cloud_timeout"
    elif is_cloud_model_error(cloud_result.response):
        status = "failure"
        error_category = "cloud_error"
    else:
        status = "success"
        error_category = None

    return ModelExecutionResult(
        response=cloud_result.response,
        status=status,
        duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
        error_category=error_category,
        metrics=ModelExecutionMetrics(prompt_chars=len(prompt)),
        provider=provider,
        model=effective_model,
    )


def get_model_provider() -> ModelProvider:
    """
    Return the active model provider selected by environment.
    """

    raw_provider = os.getenv("STS_MODEL_PROVIDER", "ollama")
    provider = raw_provider.strip().lower().replace("_", "-")
    aliases = {
        "local": "ollama",
        "cloud": "openai-compatible",
        "openai-compatible": "openai-compatible",
        "gemini": "google-ai-studio",
        "google-ai-studio": "google-ai-studio",
    }
    provider = aliases.get(provider, provider)
    if provider in {
        "ollama", "openai", "openai-compatible", "opencode", "google-ai-studio",
    }:
        return provider
    return "ollama"


def resolve_model_name(configured_model: str) -> str:
    """
    Return the active model name, allowing cloud paths to override agent config.
    """

    return os.getenv("STS_MODEL", "").strip() or configured_model


def get_cloud_model_config(provider: ModelProvider) -> CloudModelConfig | None:
    """
    Return cloud transport settings for a supported provider.
    """

    if provider == "ollama":
        return None

    if provider == "opencode":
        api_key = (
            os.getenv("STS_OPENCODE_API_KEY")
            or os.getenv("OPENCODE_API_KEY")
            or ""
        ).strip()
        base_url = (
            os.getenv("STS_OPENCODE_BASE_URL")
            or os.getenv("OPENCODE_BASE_URL")
            or "https://opencode.ai/zen/v1"
        ).strip()
    elif provider == "google-ai-studio":
        api_key = (
            os.getenv("STS_GOOGLE_AI_STUDIO_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or ""
        ).strip()
        base_url = (
            os.getenv("STS_GOOGLE_AI_STUDIO_BASE_URL")
            or "https://generativelanguage.googleapis.com/v1beta/openai"
        ).strip()
    else:
        api_key = (
            os.getenv("STS_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        ).strip()
        base_url = (
            os.getenv("STS_OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).strip()

    if not api_key or not base_url:
        return None
    return CloudModelConfig(provider=provider, api_key=api_key, base_url=base_url)


def _execute_ollama_model(
    *,
    model: str,
    prompt: str,
    temperature: float,
    num_predict: int | None,
    started_at: float,
) -> ModelExecutionResult:
    ollama_options = {
        "temperature": temperature,
    }
    if num_predict is not None:
        ollama_options["num_predict"] = num_predict

    ollama_result = run_ollama_result(
        model,
        prompt,
        **ollama_options,
    )
    response = ollama_result.response

    if response.startswith("Ollama request timed out."):
        status = "timeout"
        error_category = "ollama_timeout"
    elif is_ollama_error(response):
        status = "failure"
        error_category = "ollama_error"
    else:
        status = "success"
        error_category = None

    return ModelExecutionResult(
        response=response,
        status=status,
        duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
        error_category=error_category,
        metrics=ModelExecutionMetrics(
            total_duration_ms=ollama_result.total_duration_ms,
            load_duration_ms=ollama_result.load_duration_ms,
            prompt_eval_count=ollama_result.prompt_eval_count,
            prompt_eval_duration_ms=ollama_result.prompt_eval_duration_ms,
            eval_count=ollama_result.eval_count,
            eval_duration_ms=ollama_result.eval_duration_ms,
            prompt_tokens_per_second=ollama_result.prompt_tokens_per_second,
            output_tokens_per_second=ollama_result.output_tokens_per_second,
            prompt_chars=len(prompt),
        ),
        provider="ollama",
        model=model,
    )


def _failure_result(
    *,
    response: str,
    error_category: str,
    provider: str,
    model: str,
    prompt: str,
    started_at: float,
) -> ModelExecutionResult:
    return ModelExecutionResult(
        response=response,
        status="failure",
        duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
        error_category=error_category,
        metrics=ModelExecutionMetrics(prompt_chars=len(prompt)),
        provider=provider,
        model=model,
    )


def _missing_cloud_configuration_message(provider: str) -> str:
    if provider == "opencode":
        return (
            "Cloud model provider is not configured. "
            "Set STS_MODEL_PROVIDER=opencode, STS_MODEL, "
            "and STS_OPENCODE_API_KEY (or OPENCODE_API_KEY)."
        )
    if provider == "google-ai-studio":
        return (
            "Cloud model provider is not configured. "
            "Set STS_MODEL_PROVIDER=google-ai-studio (or gemini), "
            "STS_MODEL, and STS_GOOGLE_AI_STUDIO_API_KEY (or GEMINI_API_KEY)."
        )
    return (
        "Cloud model provider is not configured. "
        "Set STS_MODEL_PROVIDER=openai, STS_MODEL, and OPENAI_API_KEY."
    )
