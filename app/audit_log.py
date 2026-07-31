"""
Privacy-conscious audit logging for agent execution outcomes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


AUDIT_LOG_PATH = Path("data/audit/runtime.log")
PRIVILEGED_AUDIT_LOG_PATH = Path("data/audit/privileged.log")


def write_audit_record(
    *,
    agent_name: str,
    model: str,
    status: str,
    duration_ms: int,
    memory_persisted: bool,
    error_category: str | None = None,
) -> None:
    """
    Append one metadata-only audit record without affecting caller behavior.
    """

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "model": model,
        "status": status,
        "duration_ms": duration_ms,
        "memory_persisted": memory_persisted,
        "error_category": error_category,
    }

    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception:
        # Audit persistence must never disrupt the user-facing execution path.
        return


def write_privileged_action_record(
    *,
    action_type: str,
    workspace_identity: str,
    status: str,
    approval_reference: str,
    relative_path: str | None,
    operation: str | None,
) -> None:
    """
    Append metadata for one privileged action without storing file content.
    """

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "workspace_identity": workspace_identity,
        "status": status,
        "approval_reference": approval_reference,
        "relative_path": relative_path,
        "operation": operation,
    }

    try:
        PRIVILEGED_AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PRIVILEGED_AUDIT_LOG_PATH.open(
            "a",
            encoding="utf-8",
        ) as audit_file:
            audit_file.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception:
        return
