"""
Ollama HTTP client for STS AI Engine.
"""

import json
import urllib.request


OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"


def run_ollama(model: str, prompt: str) -> str:
    """
    Send a prompt to Ollama using the HTTP API.
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 1024,
            "num_predict": 120,
            "temperature": 0.2
        },
    }

    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=600) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("response", "").strip()
