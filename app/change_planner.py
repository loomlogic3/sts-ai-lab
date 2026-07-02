"""
Read-only change planner for STS AI Lab.
"""

from app.project_index import format_project_index


def plan_change(goal: str) -> str:
    """
    Create a safe, read-only implementation plan for a requested change.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /plan-change <goal>"

    project_index = format_project_index()

    return (
        "Change Plan\n\n"
        f"Goal: {goal}\n\n"
        "Current Project Context:\n"
        f"{project_index}\n\n"
        "Suggested Approach:\n"
        "1. Identify the module responsible for the requested behavior.\n"
        "2. Inspect the relevant files with /read, /grep, /functions, or /analyze.\n"
        "3. Decide which files would likely need changes.\n"
        "4. Write a human-readable plan before editing anything.\n"
        "5. Do not modify files until the user explicitly approves a patch.\n\n"
        "Safety:\n"
        "- This is a planning-only tool.\n"
        "- No files were edited.\n"
        "- No commands were executed.\n"
    )
