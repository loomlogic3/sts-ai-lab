"""
Command handlers for STS AI Lab.
"""

from app.approval import approval_required
from app.change_planner import plan_change
from app.code_understanding import (
    analyze_python_file,
    explain_file,
    list_python_classes,
    list_python_functions,
    list_python_imports,
)
from app.design_artifact import create_design
from app.experiment_logger import log_experiment
from app.experiments import list_experiments
from app.file_tools import find_todos, grep_files, project_tree, read_file, search_files
from app.knowledge_search import search_knowledge
from app.patch_drafter import draft_patch
from app.patch_proposal import propose_patch
from app.project_index import find_symbol, format_project_index, project_map
from app.proposal import create_proposal
from app.risk_analyzer import assess_risk
from app.tool_registry import format_tools


def tools_handler(args: str) -> str:
    """
    Handle the /tools command.
    """
    return format_tools()


def tree_handler(args: str) -> str:
    """
    Handle the /tree command.
    """
    return project_tree()


def read_handler(args: str) -> str:
    """
    Handle the /read command.
    """
    return read_file(args)


def search_handler(args: str) -> str:
    """Handle the /search command."""
    return search_files(args)


def grep_handler(args: str) -> str:
    """Handle the /grep command."""
    return grep_files(args)


def todos_handler(args: str) -> str:
    """Handle the /todos command."""
    return find_todos()


def plan_change_handler(args: str) -> str:
    """Handle the /plan-change command."""
    return plan_change(args)


def risk_handler(args: str) -> str:
    """Handle the /risk command."""
    return assess_risk(args)


def proposal_handler(args: str) -> str:
    """Handle the /proposal command."""
    return create_proposal(args)


def propose_patch_handler(args: str) -> str:
    """Handle the /propose-patch command."""
    return propose_patch(args)


def draft_patch_handler(args: str) -> str:
    """Handle the /draft-patch command."""
    return draft_patch(args)


def approval_required_handler(args: str) -> str:
    """Handle the /approval-required command."""
    return approval_required(args)


def design_handler(args: str) -> str:
    """Handle the /design command."""
    return create_design(args)


def explain_handler(args: str) -> str:
    """Handle the /explain command."""
    return explain_file(args)


def analyze_handler(args: str) -> str:
    """Handle the /analyze command."""
    return analyze_python_file(args)


def functions_handler(args: str) -> str:
    """Handle the /functions command."""
    return list_python_functions(args)


def classes_handler(args: str) -> str:
    """Handle the /classes command."""
    return list_python_classes(args)


def imports_handler(args: str) -> str:
    """Handle the /imports command."""
    return list_python_imports(args)


def index_handler(args: str) -> str:
    """Handle the /index command."""
    return format_project_index()


def project_map_handler(args: str) -> str:
    """Handle the /project-map command."""
    return project_map()


def where_handler(args: str) -> str:
    """Handle the /where command."""
    return find_symbol(args)


def experiments_handler(args: str) -> str:
    """Handle the /experiments command."""
    experiments = list_experiments()

    if not experiments:
        return "No experiments found."

    return "\n".join(path.name for path in experiments)


def knowledge_handler(args: str) -> str:
    """Handle the /knowledge command."""
    return search_knowledge(args) or "No knowledge found."


def log_handler(args: str) -> str:
    """Handle the /log command."""
    note = args.strip()

    if not note:
        return "Usage: /log <experiment note>"

    path = log_experiment("mentor_session_note", note)
    return f"Experiment saved: {path}"
