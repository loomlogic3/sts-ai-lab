"""
Read-only patch drafter for STS AI Lab.
"""

from app.goal_analyzer import relevant_files
from app.patch_proposal import proposed_file_changes
from app.risk_analyzer import assess_risk


def draft_patch(goal: str) -> str:
    """
    Draft a human-readable patch plan without modifying files.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /draft-patch <goal>"

    files = relevant_files(goal)

    lines = [
        "Patch Draft",
        "===========",
        "",
        f"Goal: {goal}",
        "",
        assess_risk(goal),
        "",
        "Files Likely Involved:",
    ]

    if files:
        lines.extend(f"- {file}" for file in files)
    else:
        lines.append("- No files identified yet.")

    lines.extend(
        [
            "",
            "Drafted Patch Intent:",
        ]
    )

    lines.extend(proposed_file_changes(goal))

    lines.extend(
        [
            "",
            "Not Applied:",
            "- No files were changed.",
            "- This is not an executable patch.",
            "- Human review is required before implementation.",
        ]
    )

    return "\n".join(lines)
