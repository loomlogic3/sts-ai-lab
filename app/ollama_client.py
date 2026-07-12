"""
Ollama HTTP client for STS AI Lab.
"""

import json
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_TIMEOUT_SECONDS = 60

OLLAMA_ERROR_PREFIXES = (
    "Ollama request timed out.",
    "Ollama connection failed:",
    "Ollama returned an invalid JSON response.",
)


def is_ollama_error(message: str) -> bool:
    """
    Return True when a response is an Ollama client error message.
    """
    return message.startswith(OLLAMA_ERROR_PREFIXES)



def run_ollama(
    model: str,
    prompt: str,
    num_predict: int = 120,
    temperature: float = 0.2,
) -> str:
    """
    Send a prompt to Ollama and return the response text.
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 1024,
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
        return "Ollama request timed out. Is the local model overloaded?"

    except urllib.error.URLError as error:
        return f"Ollama connection failed: {error.reason}"

    except json.JSONDecodeError:
        return "Ollama returned an invalid JSON response."

    return data.get("response", "")
