"""
Experiment Logger
"""

from datetime import datetime
from pathlib import Path

EXPERIMENT_DIR = Path("experiments")


def log_experiment(title: str, notes: str) -> Path:
    """
    Save an experiment to disk.
    """

    EXPERIMENT_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = EXPERIMENT_DIR / f"{timestamp}_{title}.md"

    filename.write_text(
        f"# {title}\n\n"
        f"Date: {datetime.now()}\n\n"
        f"## Notes\n\n"
        f"{notes}\n",
        encoding="utf-8",
    )

    return filename
