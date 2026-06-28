import subprocess


def run_ollama(model: str, prompt: str) -> str:
    """
    Send a prompt to Ollama and return the model response.
    """

    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()
