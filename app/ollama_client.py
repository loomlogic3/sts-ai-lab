"""
Ollama HTTP client for STS AI Lab.
"""

import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import (
    OLLAMA_DEFAULT_NUM_PREDICT,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_NUM_CONTEXT,
    OLLAMA_TIMEOUT_SECONDS,
)


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

OLLAMA_ERROR_PREFIXES = (
    "Ollama request timed out.",
    "Ollama connection failed:",
    "Ollama returned an invalid JSON response.",
)


@dataclass(frozen=True)
class OllamaResult:
    """Response text and normalized control metadata from Ollama."""

    response: str
    total_duration_ms: int = 0
    load_duration_ms: int = 0
    prompt_eval_count: int = 0
    prompt_eval_duration_ms: int = 0
    eval_count: int = 0
    eval_duration_ms: int = 0
    prompt_tokens_per_second: float = 0.0
    output_tokens_per_second: float = 0.0


def is_ollama_error(message: str) -> bool:
    """
    Return True when a response is an Ollama client error message.
    """
    return message.startswith(OLLAMA_ERROR_PREFIXES)



def run_ollama(
    model: str,
    prompt: str,
    num_predict: int = OLLAMA_DEFAULT_NUM_PREDICT,
    temperature: float = 0.2,
) -> str:
    """
    Send a prompt to Ollama and return the response text.
    """

    return run_ollama_result(
        model,
        prompt,
        num_predict=num_predict,
        temperature=temperature,
    ).response


def run_ollama_result(
    model: str,
    prompt: str,
    num_predict: int = OLLAMA_DEFAULT_NUM_PREDICT,
    temperature: float = 0.2,
) -> OllamaResult:
    """Send a prompt and return content-free timing metadata with its response."""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "num_ctx": OLLAMA_NUM_CONTEXT,
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as response:
            data = json.loads(response.read().decode("utf-8"))

    except TimeoutError:
        return OllamaResult(
            "Ollama request timed out. Is the local model overloaded?"
        )

    except urllib.error.URLError as error:
        return OllamaResult(f"Ollama connection failed: {error.reason}")

    except json.JSONDecodeError:
        return OllamaResult("Ollama returned an invalid JSON response.")

    total_duration = _non_negative_number(data.get("total_duration"))
    load_duration = _non_negative_number(data.get("load_duration"))
    prompt_eval_count = _non_negative_int(data.get("prompt_eval_count"))
    prompt_eval_duration = _non_negative_number(
        data.get("prompt_eval_duration")
    )
    eval_count = _non_negative_int(data.get("eval_count"))
    eval_duration = _non_negative_number(data.get("eval_duration"))

    return OllamaResult(
        response=data.get("response", ""),
        total_duration_ms=_nanoseconds_to_ms(total_duration),
        load_duration_ms=_nanoseconds_to_ms(load_duration),
        prompt_eval_count=prompt_eval_count,
        prompt_eval_duration_ms=_nanoseconds_to_ms(prompt_eval_duration),
        eval_count=eval_count,
        eval_duration_ms=_nanoseconds_to_ms(eval_duration),
        prompt_tokens_per_second=_tokens_per_second(
            prompt_eval_count,
            prompt_eval_duration,
        ),
        output_tokens_per_second=_tokens_per_second(
            eval_count,
            eval_duration,
        ),
    )


def _non_negative_number(value: object) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        return 0
    return value


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _nanoseconds_to_ms(value: int | float) -> int:
    return max(0, round(value / 1_000_000))


def _tokens_per_second(count: int, duration_ns: int | float) -> float:
    if count == 0 or duration_ns <= 0:
        return 0.0
    return round(count * 1_000_000_000 / duration_ns, 2)
