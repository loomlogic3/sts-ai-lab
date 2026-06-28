from pathlib import Path


def load_prompt(filename: str, prompt_directory: str) -> str:
    """
    Load a prompt file from disk.
    """

    path = Path(prompt_directory) / filename

    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")

    return path.read_text(encoding="utf-8")
