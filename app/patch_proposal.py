"""
Read-only patch proposal service for STS AI Lab.
"""

from app.change_planner import plan_change
from app.goal_analyzer import relevant_files
from app.risk_analyzer import assess_risk


def proposed_file_changes(goal: str) -> list[str]:
    """
    Suggest likely file-level changes without editing files.
    """

    files = relevant_files(goal)

    if not files:
        return [
            "- No specific file changes identified yet.",
            "- Use /search, /grep, /index, or /project-map for more context.",
        ]

    suggestions = []

    for file in files:
        if file == "app/cli.py":
            suggestions.append("- app/cli.py: Add or update a CLI command branch.")
        elif "knowledge" in file:
            suggestions.append(f"- {file}: Reuse or expose knowledge document loading/search behavior.")
        elif "tool" in file:
            suggestions.append(f"- {file}: Register or route the related tool command.")
        elif "memory" in file:
            suggestions.append(f"- {file}: Review memory read/write behavior before changing.")
        else:
            suggestions.append(f"- {file}: Inspect and determine the minimal required change.")

    return suggestions


def propose_patch(goal: str) -> str:
    """
    Create a read-only patch proposal without editing files.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /propose-patch <goal>"

    lines = [
        "Patch Proposal",
        "==============",
        "",
        f"Goal: {goal}",
        "",
        assess_risk(goal),
        "",
        "---",
        "",
        plan_change(goal),
        "",
        "Suggested File-Level Changes:",
    ]

    lines.extend(proposed_file_changes(goal))

    lines.extend(
        [
            "",
            "Patch Status:",
            "- Read-only proposal.",
            "- No files changed.",
            "- No patch applied.",
            "",
            "Approval Required:",
            "- Human approval is required before any patch can be applied.",
        ]
    )

    return "\n".join(lines)
