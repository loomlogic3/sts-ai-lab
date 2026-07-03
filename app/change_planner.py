"""
Read-only change planner for STS AI Lab.
"""

from app.goal_analyzer import relevant_files


def plan_change(goal: str) -> str:
    """
    Create a safe, read-only implementation plan for a requested change.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /plan-change <goal>"

    files = relevant_files(goal)

    lines = [
        "Change Plan",
        "",
        f"Goal: {goal}",
        "",
        "Relevant Files:",
    ]

    if files:
        lines.extend(f"- {file}" for file in files)
    else:
        lines.append("- No specific files identified yet.")
        lines.append("- Use /search, /grep, /index, or /project-map to inspect further.")

    lines.extend(
        [
            "",
            "Suggested Approach:",
            "1. Inspect the relevant files.",
            "2. Confirm the correct module responsibilities.",
            "3. Identify likely changes before editing.",
            "4. Prepare a patch proposal only after review.",
            "5. Apply changes only with explicit approval.",
            "",
            "Safety:",
            "- Planning only.",
            "- No files were edited.",
            "- No commands were executed.",
        ]
    )

    return "\n".join(lines)
