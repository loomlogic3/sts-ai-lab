"""
Canonical governed boundary for production Python model execution.
"""

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from app.ollama_client import is_ollama_error, run_ollama_result


ModelExecutionStatus = Literal["success", "timeout", "failure"]


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


def execute_model(
    *,
    model: str,
    prompt: str,
    temperature: float,
    num_predict: int | None = None,
) -> ModelExecutionResult:
    """
    Invoke the raw Ollama transport and classify its deterministic outcome.
    """

    started_at = perf_counter()
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
    )
