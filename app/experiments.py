"""
Experiment management for STS AI Lab.
"""

from pathlib import Path


EXPERIMENTS_DIR = Path("experiments")


def list_experiments() -> list[Path]:
    """
    Return saved experiment log files.
    """

    if not EXPERIMENTS_DIR.exists():
        return []

    return sorted(EXPERIMENTS_DIR.glob("*.md"))


def print_experiments() -> None:
    """
    Display saved experiment logs.
    """

    experiments = list_experiments()

    print("STS AI Lab Experiments")
    print()

    if not experiments:
        print("No experiments found.")
        return

    for path in experiments:
        print(f"✓ {path.name}")
