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


def stream_ollama(model: str, prompt: str) -> str:
    """
    Stream a prompt response from Ollama and return the full response.
    """

    process = subprocess.Popen(
        ["ollama", "run", model, prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    output = ""

    if process.stdout:
        for chunk in process.stdout:
            print(chunk, end="", flush=True)
            output += chunk

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"Ollama exited with code {process.returncode}")

    return output.strip()
