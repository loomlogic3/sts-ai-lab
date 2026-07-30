"""
Approval engine for STS AI Lab.
"""

import json
import os
import re
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.risk_analyzer import assess_risk
from app.workspace import Workspace


APPROVAL_DIR = Path("data/approvals")
MAX_APPROVAL_SUMMARY_CHARS = 500
MAX_APPROVAL_IDENTITY_CHARS = 128

_APPROVAL_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_ACTION_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_WORKSPACE_ID_PATTERN = re.compile(r"^workspace_[a-f0-9]{64}$")
_APPROVAL_CLAIM_LOCK = threading.Lock()


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ApprovalRequest:
    """
    Immutable control metadata for one proposed privileged action.
    """

    approval_id: str
    action_type: str
    workspace_identity: str
    requested_by: str
    summary: str
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus
    decided_by: str | None = None
    decided_at: datetime | None = None
    consumed_at: datetime | None = None


class ApprovalStore:
    """
    Local JSON persistence for approval control records.
    """

    def __init__(self, directory: Path | str = APPROVAL_DIR) -> None:
        self.directory = Path(directory)

    def save(self, approval: ApprovalRequest) -> None:
        path = self._path_for(approval.approval_id)
        if path is None:
            raise ValueError("Invalid approval identifier.")

        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(_approval_to_record(approval), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temp_path.replace(path)

    def load(self, approval_id: str) -> ApprovalRequest | None:
        path = self._path_for(approval_id)
        if path is None:
            return None

        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
            return None

        return _approval_from_record(record, expected_id=approval_id)

    def acquire_claim_lock(
        self,
        approval_id: str,
    ) -> tuple[int, Path] | None:
        path = self._path_for(approval_id)
        if path is None:
            return None

        lock_path = path.with_suffix(".claim")
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except OSError:
            return None
        return descriptor, lock_path

    def release_claim_lock(
        self,
        claim_lock: tuple[int, Path],
    ) -> None:
        descriptor, lock_path = claim_lock
        try:
            os.close(descriptor)
        finally:
            try:
                lock_path.unlink()
            except OSError:
                pass

    def _path_for(self, approval_id: object) -> Path | None:
        if (
            not isinstance(approval_id, str)
            or _APPROVAL_ID_PATTERN.fullmatch(approval_id) is None
        ):
            return None
        return self.directory / f"{approval_id}.json"


def create_approval_request(
    *,
    action_type: str,
    workspace: Workspace,
    requested_by: str,
    summary: str,
    expires_at: datetime,
    store: ApprovalStore | None = None,
    now: datetime | None = None,
) -> ApprovalRequest:
    """
    Create and persist one pending human approval request.
    """

    created_at = _utc_time(now)
    normalized_expiry = _utc_time(expires_at)
    _validate_control_metadata(
        action_type=action_type,
        workspace_identity=workspace.identity,
        requested_by=requested_by,
        summary=summary,
    )
    if normalized_expiry <= created_at:
        raise ValueError("Approval expiration must be in the future.")

    approval = ApprovalRequest(
        approval_id=uuid.uuid4().hex,
        action_type=action_type,
        workspace_identity=workspace.identity,
        requested_by=requested_by,
        summary=summary,
        created_at=created_at,
        expires_at=normalized_expiry,
        status=ApprovalStatus.PENDING,
    )
    (store or ApprovalStore()).save(approval)
    return approval


def inspect_approval_status(
    approval_id: str,
    *,
    store: ApprovalStore | None = None,
    now: datetime | None = None,
) -> ApprovalRequest | None:
    """
    Load an approval and normalize elapsed requests to expired.
    """

    active_store = store or ApprovalStore()
    approval = active_store.load(approval_id)
    if approval is None:
        return None

    current_time = _utc_time(now)
    if (
        current_time >= approval.expires_at
        and approval.status is not ApprovalStatus.EXPIRED
    ):
        approval = replace(
            approval,
            status=ApprovalStatus.EXPIRED,
            decided_at=current_time,
        )
        try:
            active_store.save(approval)
        except (OSError, ValueError):
            pass
    return approval


def approve_request(
    approval_id: str,
    *,
    decided_by: str,
    store: ApprovalStore | None = None,
    now: datetime | None = None,
) -> ApprovalRequest | None:
    """
    Record an explicit human approval decision.
    """

    return _record_decision(
        approval_id,
        status=ApprovalStatus.APPROVED,
        decided_by=decided_by,
        store=store,
        now=now,
    )


def reject_request(
    approval_id: str,
    *,
    decided_by: str,
    store: ApprovalStore | None = None,
    now: datetime | None = None,
) -> ApprovalRequest | None:
    """
    Record an explicit human rejection decision.
    """

    return _record_decision(
        approval_id,
        status=ApprovalStatus.REJECTED,
        decided_by=decided_by,
        store=store,
        now=now,
    )


def is_action_authorized(
    *,
    approval_id: str,
    action_type: str,
    workspace_identity: str,
    store: ApprovalStore | None = None,
    now: datetime | None = None,
) -> bool:
    """
    Canonical fail-closed authorization check for future privileged actions.
    """

    try:
        approval = inspect_approval_status(
            approval_id,
            store=store,
            now=now,
        )
        current_time = _utc_time(now)
        return bool(
            approval is not None
            and approval.status is ApprovalStatus.APPROVED
            and approval.expires_at > current_time
            and approval.workspace_identity == workspace_identity
            and approval.action_type == action_type
            and approval.consumed_at is None
        )
    except Exception:
        return False


def claim_action_authorization(
    *,
    approval_id: str,
    action_type: str,
    workspace_identity: str,
    store: ApprovalStore | None = None,
    now: datetime | None = None,
) -> datetime | None:
    """
    Atomically claim one approved action for single use in this process.
    """

    active_store = store or ApprovalStore()
    claimed_at = _utc_time(now)
    with _APPROVAL_CLAIM_LOCK:
        claim_lock = active_store.acquire_claim_lock(approval_id)
        if claim_lock is None:
            return None
        try:
            if not is_action_authorized(
                approval_id=approval_id,
                action_type=action_type,
                workspace_identity=workspace_identity,
                store=active_store,
                now=claimed_at,
            ):
                return None

            approval = active_store.load(approval_id)
            if approval is None or approval.consumed_at is not None:
                return None

            active_store.save(replace(approval, consumed_at=claimed_at))
            return claimed_at
        finally:
            active_store.release_claim_lock(claim_lock)


def restore_action_authorization(
    approval_id: str,
    *,
    claimed_at: datetime,
    store: ApprovalStore | None = None,
) -> bool:
    """
    Restore an exact claim when its privileged action did not complete.
    """

    active_store = store or ApprovalStore()
    with _APPROVAL_CLAIM_LOCK:
        claim_lock = active_store.acquire_claim_lock(approval_id)
        if claim_lock is None:
            return False
        try:
            approval = active_store.load(approval_id)
            if approval is None or approval.consumed_at != _utc_time(claimed_at):
                return False
            active_store.save(replace(approval, consumed_at=None))
            return True
        finally:
            active_store.release_claim_lock(claim_lock)


def _record_decision(
    approval_id: str,
    *,
    status: ApprovalStatus,
    decided_by: str,
    store: ApprovalStore | None,
    now: datetime | None,
) -> ApprovalRequest | None:
    active_store = store or ApprovalStore()
    approval = inspect_approval_status(
        approval_id,
        store=active_store,
        now=now,
    )
    if approval is None or approval.status is not ApprovalStatus.PENDING:
        return approval

    _validate_identity(decided_by, "decided_by")
    if decided_by == approval.requested_by:
        raise ValueError("Requesters cannot decide their own approval request.")

    decision = replace(
        approval,
        status=status,
        decided_by=decided_by,
        decided_at=_utc_time(now),
    )
    active_store.save(decision)
    return decision


def _approval_to_record(approval: ApprovalRequest) -> dict:
    return {
        "approval_id": approval.approval_id,
        "action_type": approval.action_type,
        "workspace_identity": approval.workspace_identity,
        "requested_by": approval.requested_by,
        "summary": approval.summary,
        "created_at": approval.created_at.isoformat(),
        "expires_at": approval.expires_at.isoformat(),
        "status": approval.status.value,
        "decided_by": approval.decided_by,
        "decided_at": (
            approval.decided_at.isoformat()
            if approval.decided_at is not None
            else None
        ),
        "consumed_at": (
            approval.consumed_at.isoformat()
            if approval.consumed_at is not None
            else None
        ),
    }


def _approval_from_record(
    record: object,
    *,
    expected_id: str,
) -> ApprovalRequest | None:
    if not isinstance(record, dict):
        return None

    try:
        approval = ApprovalRequest(
            approval_id=record["approval_id"],
            action_type=record["action_type"],
            workspace_identity=record["workspace_identity"],
            requested_by=record["requested_by"],
            summary=record["summary"],
            created_at=_parse_time(record["created_at"]),
            expires_at=_parse_time(record["expires_at"]),
            status=ApprovalStatus(record["status"]),
            decided_by=record.get("decided_by"),
            decided_at=(
                _parse_time(record["decided_at"])
                if record.get("decided_at") is not None
                else None
            ),
            consumed_at=(
                _parse_time(record["consumed_at"])
                if record.get("consumed_at") is not None
                else None
            ),
        )
        _validate_loaded_approval(approval, expected_id)
    except (KeyError, TypeError, ValueError):
        return None
    return approval


def _validate_loaded_approval(
    approval: ApprovalRequest,
    expected_id: str,
) -> None:
    if approval.approval_id != expected_id:
        raise ValueError("Approval identifier mismatch.")
    if _APPROVAL_ID_PATTERN.fullmatch(approval.approval_id) is None:
        raise ValueError("Invalid approval identifier.")
    _validate_control_metadata(
        action_type=approval.action_type,
        workspace_identity=approval.workspace_identity,
        requested_by=approval.requested_by,
        summary=approval.summary,
    )
    if approval.expires_at <= approval.created_at:
        raise ValueError("Invalid approval time range.")
    if approval.decided_by is not None:
        _validate_identity(approval.decided_by, "decided_by")
    if approval.status is ApprovalStatus.PENDING:
        if (
            approval.decided_by is not None
            or approval.decided_at is not None
            or approval.consumed_at is not None
        ):
            raise ValueError("Pending approvals cannot contain a decision.")
    if approval.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        if approval.decided_by is None or approval.decided_at is None:
            raise ValueError("Decided approvals require decision metadata.")
        if approval.decided_by == approval.requested_by:
            raise ValueError("Requesters cannot approve their own requests.")
    if (
        approval.consumed_at is not None
        and approval.status not in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.EXPIRED,
        }
    ):
        raise ValueError("Only approved requests can carry consumption metadata.")


def _validate_control_metadata(
    *,
    action_type: object,
    workspace_identity: object,
    requested_by: object,
    summary: object,
) -> None:
    if (
        not isinstance(action_type, str)
        or _ACTION_TYPE_PATTERN.fullmatch(action_type) is None
    ):
        raise ValueError("Invalid action type.")
    if (
        not isinstance(workspace_identity, str)
        or _WORKSPACE_ID_PATTERN.fullmatch(workspace_identity) is None
    ):
        raise ValueError("Invalid workspace identity.")
    _validate_identity(requested_by, "requested_by")
    if (
        not isinstance(summary, str)
        or not summary.strip()
        or len(summary) > MAX_APPROVAL_SUMMARY_CHARS
    ):
        raise ValueError("Invalid approval summary.")


def _validate_identity(value: object, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_APPROVAL_IDENTITY_CHARS
    ):
        raise ValueError(f"Invalid {field_name} identity.")


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Invalid timestamp.")
    return _utc_time(datetime.fromisoformat(value))


def _utc_time(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Timestamps must include timezone information.")
    return current.astimezone(timezone.utc)


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
