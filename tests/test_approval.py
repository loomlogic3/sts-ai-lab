import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.approval import (
    ApprovalStatus,
    ApprovalStore,
    approve_request,
    create_approval_request,
    inspect_approval_status,
    is_action_authorized,
    reject_request,
)
from app.workspace import Workspace


NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    return Workspace(root)


@pytest.fixture
def store(tmp_path):
    return ApprovalStore(tmp_path / "approvals")


def create_request(workspace, store, **overrides):
    values = {
        "action_type": "file_write",
        "workspace": workspace,
        "requested_by": "code-agent",
        "summary": "Write the reviewed configuration change.",
        "expires_at": NOW + timedelta(minutes=15),
        "store": store,
        "now": NOW,
    }
    values.update(overrides)
    return create_approval_request(**values)


def test_approval_request_creation_is_pending_and_persisted(
    workspace,
    store,
):
    approval = create_request(workspace, store)
    loaded = inspect_approval_status(
        approval.approval_id,
        store=store,
        now=NOW,
    )

    assert approval.status is ApprovalStatus.PENDING
    assert loaded == approval
    assert approval.workspace_identity == workspace.identity
    assert approval.created_at == NOW
    assert approval.expires_at == NOW + timedelta(minutes=15)
    assert (store.directory / f"{approval.approval_id}.json").exists()


def test_approval_request_is_immutable(workspace, store):
    approval = create_request(workspace, store)

    with pytest.raises(FrozenInstanceError):
        approval.status = ApprovalStatus.APPROVED


def test_approval_identifiers_are_unique_and_not_user_supplied(
    workspace,
    store,
):
    first = create_request(workspace, store)
    second = create_request(workspace, store)

    assert first.approval_id != second.approval_id
    assert len(first.approval_id) == 32
    assert "code-agent" not in first.approval_id
    assert "file_write" not in first.approval_id


def test_pending_approval_does_not_authorize(workspace, store):
    approval = create_request(workspace, store)

    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=NOW,
    )


def test_approved_matching_request_authorizes(workspace, store):
    approval = create_request(workspace, store)
    approved = approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=NOW + timedelta(minutes=1),
    )

    assert approved.status is ApprovalStatus.APPROVED
    assert approved.decided_by == "human-owner"
    assert is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=NOW + timedelta(minutes=2),
    )


def test_requester_cannot_approve_own_request(workspace, store):
    approval = create_request(workspace, store)

    with pytest.raises(ValueError, match="cannot decide"):
        approve_request(
            approval.approval_id,
            decided_by=approval.requested_by,
            store=store,
            now=NOW + timedelta(minutes=1),
        )

    assert inspect_approval_status(
        approval.approval_id,
        store=store,
        now=NOW,
    ).status is ApprovalStatus.PENDING


def test_rejected_approval_does_not_authorize(workspace, store):
    approval = create_request(workspace, store)
    rejected = reject_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=NOW + timedelta(minutes=1),
    )

    assert rejected.status is ApprovalStatus.REJECTED
    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=NOW + timedelta(minutes=2),
    )


def test_expired_pending_approval_does_not_authorize(workspace, store):
    approval = create_request(workspace, store)

    inspected = inspect_approval_status(
        approval.approval_id,
        store=store,
        now=approval.expires_at,
    )

    assert inspected.status is ApprovalStatus.EXPIRED
    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=approval.expires_at,
    )


def test_expiration_overrides_stored_approved_status(workspace, store):
    approval = create_request(workspace, store)
    approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=NOW + timedelta(minutes=1),
    )

    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=approval.expires_at + timedelta(seconds=1),
    )
    assert inspect_approval_status(
        approval.approval_id,
        store=store,
        now=approval.expires_at + timedelta(seconds=1),
    ).status is ApprovalStatus.EXPIRED


def test_workspace_mismatch_blocks_authorization(
    workspace,
    store,
    tmp_path,
):
    other_root = tmp_path / "other"
    other_root.mkdir()
    other_workspace = Workspace(other_root)
    approval = create_request(workspace, store)
    approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=NOW + timedelta(minutes=1),
    )

    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=other_workspace.identity,
        store=store,
        now=NOW + timedelta(minutes=2),
    )


def test_action_type_mismatch_blocks_authorization(workspace, store):
    approval = create_request(workspace, store)
    approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=NOW + timedelta(minutes=1),
    )

    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="command_run",
        workspace_identity=workspace.identity,
        store=store,
        now=NOW + timedelta(minutes=2),
    )


def test_unknown_or_unsafe_approval_id_fails_closed(workspace, store):
    for approval_id in ("0" * 32, "../approval", "/tmp/approval"):
        assert not is_action_authorized(
            approval_id=approval_id,
            action_type="file_write",
            workspace_identity=workspace.identity,
            store=store,
            now=NOW,
        )


def test_invalid_authorization_time_fails_closed(workspace, store):
    approval = create_request(workspace, store)

    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=datetime(2026, 7, 27, 12, 1),
    )


def test_malformed_stored_approval_fails_closed(workspace, store):
    approval_id = "a" * 32
    store.directory.mkdir(parents=True)
    (store.directory / f"{approval_id}.json").write_text(
        '{"status": "approved", "workspace_identity": ',
        encoding="utf-8",
    )

    assert inspect_approval_status(
        approval_id,
        store=store,
        now=NOW,
    ) is None
    assert not is_action_authorized(
        approval_id=approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=NOW,
    )


def test_approved_request_cannot_change_workspace_silently(
    workspace,
    store,
):
    approval = create_request(workspace, store)
    approved = approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=NOW + timedelta(minutes=1),
    )

    assert approved.workspace_identity == approval.workspace_identity
    assert approved.action_type == approval.action_type
    with pytest.raises(FrozenInstanceError):
        approved.workspace_identity = "workspace_" + ("0" * 64)


def test_tampered_self_approval_fails_closed(workspace, store):
    approval = create_request(workspace, store)
    tampered = replace(
        approval,
        status=ApprovalStatus.APPROVED,
        decided_by=approval.requested_by,
        decided_at=NOW + timedelta(minutes=1),
    )
    path = store.directory / f"{approval.approval_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update({
        "status": tampered.status.value,
        "decided_by": tampered.decided_by,
        "decided_at": tampered.decided_at.isoformat(),
    })
    path.write_text(json.dumps(record), encoding="utf-8")

    assert not is_action_authorized(
        approval_id=approval.approval_id,
        action_type="file_write",
        workspace_identity=workspace.identity,
        store=store,
        now=NOW + timedelta(minutes=2),
    )


def test_approval_record_contains_control_metadata_only(workspace, store):
    approval = create_request(workspace, store)
    path = store.directory / f"{approval.approval_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))

    assert set(record) == {
        "approval_id",
        "action_type",
        "workspace_identity",
        "requested_by",
        "summary",
        "created_at",
        "expires_at",
        "status",
        "decided_by",
        "decided_at",
    }
    for forbidden_field in (
        "prompt",
        "model_response",
        "conversation",
        "source_file",
        "secret",
        "token",
        "password",
    ):
        assert forbidden_field not in record


def test_raw_workspace_path_is_not_required_or_persisted(workspace, store):
    approval = create_request(workspace, store)
    serialized = (
        store.directory / f"{approval.approval_id}.json"
    ).read_text(encoding="utf-8")

    assert str(workspace.root) not in serialized
    assert is_action_authorized(
        approval_id=approval.approval_id,
        action_type=approval.action_type,
        workspace_identity=workspace.identity,
        store=store,
        now=NOW,
    ) is False


def test_no_privileged_engineering_action_is_introduced():
    source = Path("app/approval.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    direct_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert "subprocess" not in direct_imports
    assert "app.file_tools" not in imported_modules
    assert "app.command_registry" not in imported_modules
    assert "app.tool_router" not in imported_modules
    assert "is_action_authorized" in source


def test_canonical_authorization_checks_all_required_bindings():
    source = ast.parse(
        Path("app/approval.py").read_text(encoding="utf-8")
    )
    function = next(
        node
        for node in source.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "is_action_authorized"
    )
    function_text = ast.unparse(function)

    assert "ApprovalStatus.APPROVED" in function_text
    assert "workspace_identity" in function_text
    assert "action_type" in function_text
    assert "expires_at" in function_text
