"""
Read-only patch proposal service for STS AI Lab.
"""

from app.change_planner import plan_change
from app.risk_analyzer import assess_risk


def propose_patch(goal: str) -> str:
    """
    Create a read-only patch proposal without editing files.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /propose-patch <goal>"

    return (
        "Patch Proposal\n"
        "==============\n\n"
        f"Goal: {goal}\n\n"
        f"{assess_risk(goal)}\n\n"
        "---\n\n"
        f"{plan_change(goal)}\n\n"
        "Patch Draft:\n"
        "- No patch generated yet.\n"
        "- Next version will suggest file-level changes.\n"
        "- This tool is read-only and does not modify files.\n\n"
        "Approval Required:\n"
        "- Human approval is required before any patch can be applied."
    )
