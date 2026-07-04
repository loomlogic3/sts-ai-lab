"""
Approval engine for STS AI Lab.
"""

from app.risk_analyzer import assess_risk


def approval_required(goal: str) -> str:
    """
    Determine whether explicit human approval is required.
    """

    goal = goal.strip()

    if not goal:
        return "Usage: /approval-required <goal>"

    risk = assess_risk(goal)

    return (
        "Approval Decision\n"
        "=================\n\n"
        f"Goal: {goal}\n\n"
        f"{risk}\n\n"
        "Decision:\n"
        "✓ Human approval REQUIRED\n\n"
        "Reason:\n"
        "- STS Human-Supervised Intelligence Architecture\n"
        "- No autonomous code changes permitted\n"
        "- Execution cannot continue without approval"
    )
