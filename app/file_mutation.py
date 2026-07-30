"""
Approval-gated, workspace-contained text-file mutation.
"""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.approval import (
    ApprovalStore,
    claim_action_authorization,
    restore_action_authorization,
)
from app.audit_log import write_privileged_action_record
from app.workspace import Workspace


FILE_WRITE_ACTION = "file_write"
FileMutationStatus = Literal[
    "success",
    "not_authorized",
    "invalid_target",
    "write_failure",
]
FileMutationOperation = Literal["created", "replaced"]


@dataclass(frozen=True)
class FileMutationResult:
    """
    Safe metadata returned by one controlled file-write attempt.
    """

    status: FileMutationStatus
    workspace_identity: str
    relative_path: str | None
    operation: FileMutationOperation | None


def write_text_file(
    *,
    workspace: Workspace,
    relative_path: str,
    content: str,
    approval_id: str,
    approval_store: ApprovalStore | None = None,
) -> FileMutationResult:
    """
    Create or replace one UTF-8 text file after single-use authorization.
    """

    approval_reference = _approval_reference(approval_id)
    target = workspace.resolve_path(relative_path)
    if not isinstance(content, str) or not _valid_target(target):
        return _result(
            status="invalid_target",
            workspace=workspace,
            relative_path=None,
            operation=None,
            approval_reference=approval_reference,
        )

    safe_relative_path = str(target.relative_to(workspace.root))
    operation: FileMutationOperation = (
        "replaced" if target.exists() else "created"
    )

    try:
        claimed_at = claim_action_authorization(
            approval_id=approval_id,
            action_type=FILE_WRITE_ACTION,
            workspace_identity=workspace.identity,
            store=approval_store,
        )
    except Exception:
        claimed_at = None

    if claimed_at is None:
        return _result(
            status="not_authorized",
            workspace=workspace,
            relative_path=safe_relative_path,
            operation=None,
            approval_reference=approval_reference,
        )

    temp_path: Path | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".sts-write-",
            suffix=".tmp",
            dir=target.parent,
            text=True,
        )
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        _atomic_replace(temp_path, target)
    except (OSError, UnicodeError):
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            restore_action_authorization(
                approval_id,
                claimed_at=claimed_at,
                store=approval_store,
            )
        except Exception:
            pass
        return _result(
            status="write_failure",
            workspace=workspace,
            relative_path=safe_relative_path,
            operation=None,
            approval_reference=approval_reference,
        )

    return _result(
        status="success",
        workspace=workspace,
        relative_path=safe_relative_path,
        operation=operation,
        approval_reference=approval_reference,
    )


def _valid_target(target: Path | None) -> bool:
    if target is None or not target.parent.is_dir():
        return False
    if target.exists() and not target.is_file():
        return False
    return True


def _atomic_replace(source: Path, target: Path) -> None:
    os.replace(source, target)


def _approval_reference(approval_id: object) -> str:
    value = approval_id if isinstance(approval_id, str) else ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _result(
    *,
    status: FileMutationStatus,
    workspace: Workspace,
    relative_path: str | None,
    operation: FileMutationOperation | None,
    approval_reference: str,
) -> FileMutationResult:
    result = FileMutationResult(
        status=status,
        workspace_identity=workspace.identity,
        relative_path=relative_path,
        operation=operation,
    )
    write_privileged_action_record(
        action_type=FILE_WRITE_ACTION,
        workspace_identity=workspace.identity,
        status=status,
        approval_reference=approval_reference,
        relative_path=relative_path,
        operation=operation,
    )
    return result
