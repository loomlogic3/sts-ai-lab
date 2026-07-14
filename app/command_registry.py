"""
Command registry for STS AI Lab.

Maps command names to handler functions.
"""

from app.command_handlers import (
    analyze_handler,
    approval_required_handler,
    classes_handler,
    design_handler,
    draft_patch_handler,
    experiments_handler,
    explain_handler,
    functions_handler,
    grep_handler,
    imports_handler,
    index_handler,
    knowledge_handler,
    log_handler,
    plan_change_handler,
    project_map_handler,
    proposal_handler,
    propose_patch_handler,
    read_handler,
    risk_handler,
    search_handler,
    todos_handler,
    tools_handler,
    tree_handler,
    where_handler,
)


COMMANDS = {}


def register(command: str, handler):
    """
    Register a command handler.
    """
    COMMANDS[command] = handler


def get_handler(command: str):
    """
    Return the registered handler, or None.
    """
    return COMMANDS.get(command)


def list_registered_commands():
    """
    Return registered command names.
    """
    return sorted(COMMANDS.keys())


register("/tools", tools_handler)

register("/tree", tree_handler)

register("/read", read_handler)

register("/search", search_handler)

register("/grep", grep_handler)

register("/todos", todos_handler)

register("/plan-change", plan_change_handler)

register("/risk", risk_handler)

register("/proposal", proposal_handler)

register("/propose-patch", propose_patch_handler)

register("/draft-patch", draft_patch_handler)

register("/approval-required", approval_required_handler)

register("/design", design_handler)

register("/explain", explain_handler)

register("/analyze", analyze_handler)

register("/functions", functions_handler)

register("/classes", classes_handler)

register("/imports", imports_handler)

register("/index", index_handler)

register("/project-map", project_map_handler)

register("/where", where_handler)

register("/experiments", experiments_handler)

register("/knowledge", knowledge_handler)

register("/log", log_handler)
