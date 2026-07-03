"""
Read-only change proposal service for STS AI Lab.
"""

from app.change_planner import plan_change
from app.risk_analyzer import assess_risk


def create_proposal(goal: str) -> str:
    """
    Create a read-only change proposal.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /proposal <goal>"

    return (
        "Change Proposal\n"
        "===============\n\n"
        f"{assess_risk(goal)}\n\n"
        "---\n\n"
        f"{plan_change(goal)}\n\n"
        "Proposal Status:\n"
        "- Read-only.\n"
        "- No files changed.\n"
        "- Human approval required before any patching."
    )
