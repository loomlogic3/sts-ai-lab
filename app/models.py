"""
Model management for STS AI Lab.
"""

import json
from pathlib import Path


AGENTS_DIR = Path("agents")


def print_models() -> None:
    """
    Display models currently configured for each agent.
    """

    print("STS AI Lab Models")
    print()

    for path in sorted(AGENTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())

        print(f"✓ {path.stem}")
        print(f"  Model       : {data.get('model', 'unknown')}")
        print(f"  Temperature : {data.get('temperature', 'default')}")
        print()
