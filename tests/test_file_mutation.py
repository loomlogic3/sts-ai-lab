import ast
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import audit_log, file_mutation
from app.approval import (
    ApprovalStore,
    approve_request,
    create_approval_request,
    inspect_approval_status,
    reject_request,
)
from app.file_mutation import write_text_file
from app.workspace import Workspace


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    return Workspace(root)


@pytest.fixture
def store(tmp_path):
    return ApprovalStore(tmp_path / "approvals")


@pytest.fixture
def audit_path(tmp_path, monkeypatch):
    path = tmp_path / "privileged.log"
    monkeypatch.setattr(audit_log, "PRIVILEGED_AUDIT_LOG_PATH", path)
    return path


def approved_file_write(workspace, store, *, action_type="file_write"):
    now = datetime.now(timezone.utc)
    approval = create_approval_request(
        action_type=action_type,
        workspace=workspace,
        requested_by="code-agent",
        summary="Write one reviewed text file.",
        expires_at=now + timedelta(hours=1),
        store=store,
        now=now,
    )
    approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=now + timedelta(seconds=1),
    )
    return approval


def test_authorized_new_file_creation(workspace, store, audit_path):
    approval = approved_file_write(workspace, store)

    result = write_text_file(
        workspace=workspace,
        relative_path="new.txt",
        content="created content\n",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "success"
    assert result.workspace_identity == workspace.identity
    assert result.relative_path == "new.txt"
    assert result.operation == "created"
    assert (workspace.root / "new.txt").read_text(encoding="utf-8") == (
        "created content\n"
    )


def test_authorized_existing_file_replacement(workspace, store, audit_path):
    target = workspace.root / "existing.txt"
    target.write_text("old content", encoding="utf-8")
    approval = approved_file_write(workspace, store)

    result = write_text_file(
        workspace=workspace,
        relative_path="existing.txt",
        content="replacement",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "success"
    assert result.operation == "replaced"
    assert target.read_text(encoding="utf-8") == "replacement"


def test_missing_approval_blocks_write(workspace, store, audit_path):
    result = write_text_file(
        workspace=workspace,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id="0" * 32,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


def test_pending_approval_blocks_write(workspace, store, audit_path):
    now = datetime.now(timezone.utc)
    approval = create_approval_request(
        action_type="file_write",
        workspace=workspace,
        requested_by="code-agent",
        summary="Pending write.",
        expires_at=now + timedelta(hours=1),
        store=store,
        now=now,
    )

    result = write_text_file(
        workspace=workspace,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


def test_rejected_approval_blocks_write(workspace, store, audit_path):
    now = datetime.now(timezone.utc)
    approval = create_approval_request(
        action_type="file_write",
        workspace=workspace,
        requested_by="code-agent",
        summary="Rejected write.",
        expires_at=now + timedelta(hours=1),
        store=store,
        now=now,
    )
    reject_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=now + timedelta(seconds=1),
    )

    result = write_text_file(
        workspace=workspace,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


def test_expired_approval_blocks_write(workspace, store, audit_path):
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    approval = create_approval_request(
        action_type="file_write",
        workspace=workspace,
        requested_by="code-agent",
        summary="Expired write.",
        expires_at=past + timedelta(minutes=10),
        store=store,
        now=past,
    )
    approve_request(
        approval.approval_id,
        decided_by="human-owner",
        store=store,
        now=past + timedelta(minutes=1),
    )

    result = write_text_file(
        workspace=workspace,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


def test_wrong_action_type_blocks_write(workspace, store, audit_path):
    approval = approved_file_write(
        workspace,
        store,
        action_type="command_run",
    )

    result = write_text_file(
        workspace=workspace,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


def test_wrong_workspace_blocks_write(tmp_path, store, audit_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first = Workspace(first_root)
    second = Workspace(second_root)
    approval = approved_file_write(first, store)

    result = write_text_file(
        workspace=second,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (second.root / "blocked.txt").exists()


def test_malformed_approval_blocks_write(workspace, store, audit_path):
    approval_id = "a" * 32
    store.directory.mkdir()
    (store.directory / f"{approval_id}.json").write_text(
        '{"status": "approved"',
        encoding="utf-8",
    )

    result = write_text_file(
        workspace=workspace,
        relative_path="blocked.txt",
        content="must not appear",
        approval_id=approval_id,
        approval_store=store,
    )

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


@pytest.mark.parametrize(
    "path",
    [
        "/tmp/outside.txt",
        "../outside.txt",
        ".git/config",
        "data/private.txt",
        "__pycache__/private.txt",
        ".env",
    ],
)
def test_unsafe_targets_are_blocked(
    workspace,
    store,
    audit_path,
    path,
):
    approval = approved_file_write(workspace, store)

    result = write_text_file(
        workspace=workspace,
        relative_path=path,
        content="must not appear",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "invalid_target"
    assert result.relative_path is None
    assert (
        inspect_approval_status(
            approval.approval_id,
            store=store,
        ).consumed_at
        is None
    )


def test_symlink_escape_is_blocked(workspace, store, audit_path, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("outside original", encoding="utf-8")
    link = workspace.root / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable")
    approval = approved_file_write(workspace, store)

    result = write_text_file(
        workspace=workspace,
        relative_path="escape.txt",
        content="must not escape",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "invalid_target"
    assert outside.read_text(encoding="utf-8") == "outside original"


def test_valid_internal_symlink_follows_workspace_policy(
    workspace,
    store,
    audit_path,
):
    target = workspace.root / "target.txt"
    target.write_text("old", encoding="utf-8")
    link = workspace.root / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    approval = approved_file_write(workspace, store)

    result = write_text_file(
        workspace=workspace,
        relative_path="link.txt",
        content="new",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "success"
    assert result.relative_path == "target.txt"
    assert target.read_text(encoding="utf-8") == "new"
    assert link.is_symlink()


def test_utf8_content_is_written_deterministically(
    workspace,
    store,
    audit_path,
):
    approval = approved_file_write(workspace, store)
    content = "Hello, Καλημέρα, こんにちは 🌍\n"

    result = write_text_file(
        workspace=workspace,
        relative_path="unicode.txt",
        content=content,
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "success"
    assert (workspace.root / "unicode.txt").read_bytes() == content.encode(
        "utf-8"
    )


def test_failed_replace_does_not_corrupt_existing_file(
    workspace,
    store,
    audit_path,
    monkeypatch,
):
    target = workspace.root / "existing.txt"
    target.write_text("original", encoding="utf-8")
    approval = approved_file_write(workspace, store)

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(file_mutation, "_atomic_replace", fail_replace)

    result = write_text_file(
        workspace=workspace,
        relative_path="existing.txt",
        content="replacement",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "write_failure"
    assert target.read_text(encoding="utf-8") == "original"
    assert list(workspace.root.glob(".sts-write-*.tmp")) == []
    assert (
        inspect_approval_status(
            approval.approval_id,
            store=store,
        ).consumed_at
        is None
    )


def test_content_type_is_rejected_without_consuming_approval(
    workspace,
    store,
    audit_path,
):
    approval = approved_file_write(workspace, store)

    result = write_text_file(
        workspace=workspace,
        relative_path="binary.txt",
        content=b"binary",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "invalid_target"
    assert not (workspace.root / "binary.txt").exists()
    assert (
        inspect_approval_status(
            approval.approval_id,
            store=store,
        ).consumed_at
        is None
    )


def test_success_consumes_approval_for_single_use(
    workspace,
    store,
    audit_path,
):
    approval = approved_file_write(workspace, store)

    first = write_text_file(
        workspace=workspace,
        relative_path="first.txt",
        content="first",
        approval_id=approval.approval_id,
        approval_store=store,
    )
    second = write_text_file(
        workspace=workspace,
        relative_path="second.txt",
        content="second",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert first.status == "success"
    assert second.status == "not_authorized"
    assert (workspace.root / "first.txt").exists()
    assert not (workspace.root / "second.txt").exists()
    assert inspect_approval_status(
        approval.approval_id,
        store=store,
    ).consumed_at is not None


def test_existing_claim_lock_fails_closed(
    workspace,
    store,
    audit_path,
):
    approval = approved_file_write(workspace, store)
    claim_lock = store.acquire_claim_lock(approval.approval_id)
    assert claim_lock is not None

    try:
        result = write_text_file(
            workspace=workspace,
            relative_path="blocked.txt",
            content="must not appear",
            approval_id=approval.approval_id,
            approval_store=store,
        )
    finally:
        store.release_claim_lock(claim_lock)

    assert result.status == "not_authorized"
    assert not (workspace.root / "blocked.txt").exists()


def test_file_content_is_absent_from_approval_and_audit_metadata(
    workspace,
    store,
    audit_path,
):
    private_content = "PRIVATE-FILE-CONTENT-DO-NOT-LOG"
    approval = approved_file_write(workspace, store)

    write_text_file(
        workspace=workspace,
        relative_path="private.txt",
        content=private_content,
        approval_id=approval.approval_id,
        approval_store=store,
    )

    approval_record = (
        store.directory / f"{approval.approval_id}.json"
    ).read_text(encoding="utf-8")
    audit_record = audit_path.read_text(encoding="utf-8")
    assert private_content not in approval_record
    assert private_content not in audit_record
    assert approval.approval_id not in audit_record


def test_privileged_audit_contains_safe_control_metadata(
    workspace,
    store,
    audit_path,
):
    approval = approved_file_write(workspace, store)

    write_text_file(
        workspace=workspace,
        relative_path="audited.txt",
        content="content",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    record = json.loads(audit_path.read_text(encoding="utf-8"))
    assert set(record) == {
        "timestamp",
        "action_type",
        "workspace_identity",
        "status",
        "approval_reference",
        "relative_path",
        "operation",
    }
    assert record["action_type"] == "file_write"
    assert record["workspace_identity"] == workspace.identity
    assert record["status"] == "success"
    assert record["relative_path"] == "audited.txt"
    assert record["operation"] == "created"


def test_audit_failure_does_not_undo_authorized_write(
    workspace,
    store,
    monkeypatch,
):
    approval = approved_file_write(workspace, store)
    monkeypatch.setattr(
        audit_log,
        "PRIVILEGED_AUDIT_LOG_PATH",
        workspace.root,
    )

    result = write_text_file(
        workspace=workspace,
        relative_path="completed.txt",
        content="completed",
        approval_id=approval.approval_id,
        approval_store=store,
    )

    assert result.status == "success"
    assert (workspace.root / "completed.txt").read_text(
        encoding="utf-8"
    ) == "completed"


def test_existing_read_only_file_tools_remain_separate():
    source = Path("app/file_tools.py").read_text(encoding="utf-8")

    assert "write_text_file" not in source
    assert "claim_action_authorization" not in source


def test_privileged_file_write_has_canonical_guards():
    source = ast.parse(
        Path("app/file_mutation.py").read_text(encoding="utf-8")
    )
    imported_names = {
        alias.name
        for node in ast.walk(source)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(source)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(source)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }

    assert "claim_action_authorization" in imported_names
    assert "restore_action_authorization" in imported_names
    assert "resolve_path" in calls
    assert "replace" in calls


def test_no_independent_privileged_file_writer_exists():
    persistence_modules = {
        "approval.py",
        "audit_log.py",
        "experiment_logger.py",
        "memory.py",
    }
    violations = []

    for path in sorted(Path("app").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function_name = None
            if isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                function_name = node.func.id

            if function_name in {"write_text", "write_bytes", "replace"}:
                if (
                    path.name not in persistence_modules
                    and path.name != "file_mutation.py"
                    and path.name != "response_processor.py"
                ):
                    violations.append(f"{path}:{function_name}")

    assert violations == []
