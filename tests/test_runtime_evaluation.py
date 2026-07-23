import json

from app import runtime_evaluation


def audit_record(
    *,
    status="success",
    duration_ms=10,
    memory_persisted=True,
    **extra,
):
    return {
        "timestamp": "2026-07-23T12:00:00+00:00",
        "agent_name": "code_agent",
        "model": "canonical-model",
        "status": status,
        "duration_ms": duration_ms,
        "memory_persisted": memory_persisted,
        "error_category": None,
        **extra,
    }


def write_records(path, records):
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )


def test_empty_audit_state_returns_zero_metrics(tmp_path):
    summary = runtime_evaluation.evaluate_runtime(tmp_path / "missing.log")

    assert summary == runtime_evaluation.empty_evaluation()


def test_success_aggregation():
    summary = runtime_evaluation.aggregate_runtime_evaluations(
        [audit_record()]
    )

    assert summary["total_executions"] == 1
    assert summary["success_count"] == 1
    assert summary["failure_count"] == 0


def test_failure_aggregation():
    summary = runtime_evaluation.aggregate_runtime_evaluations(
        [
            audit_record(
                status="failure",
                memory_persisted=False,
                error_category="ollama_error",
            )
        ]
    )

    assert summary["failure_count"] == 1
    assert summary["success_count"] == 0


def test_timeout_aggregation():
    summary = runtime_evaluation.aggregate_runtime_evaluations(
        [
            audit_record(
                status="timeout",
                memory_persisted=False,
                error_category="ollama_timeout",
            )
        ]
    )

    assert summary["timeout_count"] == 1


def test_blocked_aggregation():
    summary = runtime_evaluation.aggregate_runtime_evaluations(
        [
            audit_record(
                status="blocked",
                memory_persisted=False,
                error_category="tool_not_allowed",
            )
        ]
    )

    assert summary["blocked_count"] == 1


def test_average_duration_and_success_rate():
    summary = runtime_evaluation.aggregate_runtime_evaluations(
        [
            audit_record(duration_ms=10),
            audit_record(
                status="failure",
                duration_ms=20,
                memory_persisted=False,
            ),
            audit_record(duration_ms=30),
        ]
    )

    assert summary["average_duration_ms"] == 20.0
    assert summary["success_rate"] == 2 / 3


def test_memory_persistence_metrics():
    summary = runtime_evaluation.aggregate_runtime_evaluations(
        [
            audit_record(memory_persisted=True),
            audit_record(memory_persisted=False),
            audit_record(memory_persisted=True),
            audit_record(memory_persisted=False),
        ]
    )

    assert summary["memory_persistence_count"] == 2
    assert summary["memory_persistence_rate"] == 0.5


def test_malformed_audit_records_are_skipped(tmp_path):
    audit_path = tmp_path / "runtime.log"
    audit_path.write_text(
        '{"status": "success"\n'
        + json.dumps(audit_record())
        + "\n"
        + json.dumps(audit_record(duration_ms=-1))
        + "\n",
        encoding="utf-8",
    )

    summary = runtime_evaluation.evaluate_runtime(audit_path)

    assert summary["total_executions"] == 1
    assert summary["success_count"] == 1


def test_evaluation_retains_only_permitted_metadata(tmp_path):
    audit_path = tmp_path / "runtime.log"
    private_values = {
        "prompt": "private prompt",
        "user_message": "private question",
        "conversation": "private conversation",
        "knowledge": "private knowledge",
        "response": "private response",
        "tool_arguments": "private arguments",
        "secret": "private secret",
        "token": "private token",
        "file_contents": "private file",
    }
    write_records(audit_path, [audit_record(**private_values)])

    records = runtime_evaluation.load_audit_metadata(audit_path)

    assert len(records) == 1
    assert set(records[0]) == set(runtime_evaluation.AUDIT_METADATA_FIELDS)
    for private_value in private_values.values():
        assert private_value not in records[0].values()


def test_evaluation_read_failure_returns_empty_state(tmp_path, monkeypatch):
    audit_path = tmp_path / "runtime.log"
    audit_path.touch()

    def fail_open(*args, **kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(runtime_evaluation.Path, "open", fail_open)

    assert (
        runtime_evaluation.evaluate_runtime(audit_path)
        == runtime_evaluation.empty_evaluation()
    )
