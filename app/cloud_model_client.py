"""
OpenAI-compatible cloud model client for STS AI Lab.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import CLOUD_MODEL_TIMEOUT_SECONDS


CLOUD_MODEL_ERROR_PREFIXES = (
    "Cloud model provider is not configured.",
    "Cloud model request timed out.",
    "Cloud model request failed:",
    "Cloud model returned an invalid JSON response.",
    "Cloud model returned an invalid response shape.",
)


@dataclass(frozen=True)
class CloudModelConfig:
    """Resolved cloud provider transport settings."""

    provider: str
    api_key: str
    base_url: str


@dataclass(frozen=True)
class CloudModelResult:
    """Response text returned by a cloud model provider."""

    response: str


def is_cloud_model_error(message: str) -> bool:
    """
    Return True when a response is a cloud model client error message.
    """

    return message.startswith(CLOUD_MODEL_ERROR_PREFIXES)


def run_cloud_model_result(
    *,
    config: CloudModelConfig,
    model: str,
    prompt: str,
    temperature: float = 0.2,
    num_predict: int | None = None,
) -> CloudModelResult:
    """
    Send a prompt to an OpenAI-compatible chat-completions provider.
    """

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
    }
    if num_predict is not None and config.provider != "google-ai-studio":
        payload["max_tokens"] = num_predict

    request = urllib.request.Request(
        _chat_completions_url(config.base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "sts-ai-lab/1.0",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=CLOUD_MODEL_TIMEOUT_SECONDS,
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except TimeoutError:
        return CloudModelResult(
            "Cloud model request timed out. Is the provider overloaded?"
        )
    except urllib.error.HTTPError as error:
        return CloudModelResult(
            f"Cloud model request failed: HTTP {error.code}"
        )
    except urllib.error.URLError as error:
        return CloudModelResult(f"Cloud model request failed: {error.reason}")
    except json.JSONDecodeError:
        return CloudModelResult(
            "Cloud model returned an invalid JSON response."
        )

    content = _extract_chat_message(data)
    if content is None:
        return CloudModelResult(
            "Cloud model returned an invalid response shape."
        )
    return CloudModelResult(content)


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _extract_chat_message(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    return content
