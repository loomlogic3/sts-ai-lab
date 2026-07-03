"""
Risk analyzer for STS AI Lab change planning.
"""


HIGH_RISK_KEYWORDS = (
    "delete",
    "remove",
    "security",
    "auth",
    "password",
    "secret",
    "token",
    "key",
    "payment",
    "wallet",
    "trade",
    "execute",
    "production",
)

MEDIUM_RISK_KEYWORDS = (
    "edit",
    "modify",
    "refactor",
    "api",
    "database",
    "memory",
    "model",
    "config",
    "router",
    "tool",
)

LOW_RISK_KEYWORDS = (
    "list",
    "show",
    "display",
    "document",
    "read",
    "search",
    "status",
)


def assess_risk(goal: str) -> str:
    """
    Assess risk level for a requested change.
    """

    goal_lower = goal.lower()

    if any(keyword in goal_lower for keyword in HIGH_RISK_KEYWORDS):
        level = "HIGH"
        reason = "The goal touches sensitive, destructive, production, financial, or security-related behavior."
    elif any(keyword in goal_lower for keyword in MEDIUM_RISK_KEYWORDS):
        level = "MEDIUM"
        reason = "The goal may affect core application behavior or shared infrastructure."
    elif any(keyword in goal_lower for keyword in LOW_RISK_KEYWORDS):
        level = "LOW"
        reason = "The goal appears informational, read-only, or documentation-focused."
    else:
        level = "UNKNOWN"
        reason = "Not enough information to confidently assess risk."

    return (
        "Risk Assessment\n\n"
        f"Goal: {goal}\n\n"
        f"Risk Level: {level}\n"
        f"Reason: {reason}\n\n"
        "Safety Rule:\n"
        "- Higher risk changes require more inspection, clearer planning, and explicit approval."
    )
