"""
Engineering design artifact generator for STS AI Lab.
"""

from app.approval import approval_required
from app.goal_analyzer import relevant_files
from app.risk_analyzer import assess_risk


def create_design(goal: str) -> str:
    """
    Create a reviewable engineering design without changing files.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /design <goal>"

    files = relevant_files(goal)

    lines = [
        "Engineering Design",
        "==================",
        "",
        f"Goal: {goal}",
        "",
        "Problem Statement:",
        f"- Implement or support: {goal}",
        "",
        "Relevant Files:",
    ]

    if files:
        lines.extend(f"- {file}" for file in files)
    else:
        lines.append("- No specific files identified yet.")

    lines.extend(
        [
            "",
            "Risk Review:",
            assess_risk(goal),
            "",
            "Approval Review:",
            approval_required(goal),
            "",
            "Implementation Strategy:",
            "1. Inspect the relevant files.",
            "2. Confirm existing responsibilities.",
            "3. Keep the change minimal.",
            "4. Draft a patch for review.",
            "5. Apply only after explicit approval.",
            "",
            "Verification Plan:",
            "- Run the affected command or workflow.",
            "- Check git status.",
            "- Confirm no unrelated files changed.",
            "",
            "Status:",
            "- Design only.",
            "- No files changed.",
            "- No patch generated.",
        ]
    )

    return "\n".join(lines)
