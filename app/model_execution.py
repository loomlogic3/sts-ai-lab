"""
Canonical governed boundary for production Python model execution.
"""

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from app.ollama_client import is_ollama_error, run_ollama


ModelExecutionStatus = Literal["success", "timeout", "failure"]


@dataclass(frozen=True)
class ModelExecutionResult:
    """
    Content and metadata returned by one governed model invocation.
    """

    response: str
    status: ModelExecutionStatus
    duration_ms: int
    error_category: str | None = None


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

    response = run_ollama(
        model,
        prompt,
        **ollama_options,
    )

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
    )
