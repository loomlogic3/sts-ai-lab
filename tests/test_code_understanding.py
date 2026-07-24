import json

from app import (
    audit_log,
    code_understanding,
    command_registry,
    runtime_evaluation,
    tool_router,
)
from app.memory import ConversationMemory
from app.model_execution import ModelExecutionResult


class FakeMemory:
    def context(self):
        return ""


def test_code_explanation_uses_canonical_model_configuration_and_audits_once(
    tmp_path,
    monkeypatch,
):
    audit_path = tmp_path / "runtime.log"
    captured = {}
    private_source = "private file contents"
    private_response = "private model response"

    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", audit_path)
    monkeypatch.setattr(
        code_understanding,
        "read_file",
        lambda path: private_source,
    )
    monkeypatch.setattr(
        code_understanding,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-code-model",
            "temperature": 0.45,
        },
    )

    def fake_execute_model(**options):
        captured.update(options)
        return ModelExecutionResult(
            private_response,
            "success",
            12,
        )

    monkeypatch.setattr(
        code_understanding,
        "execute_model",
        fake_execute_model,
    )
    monkeypatch.setattr(
        ConversationMemory,
        "save",
        lambda self: (_ for _ in ()).throw(
            AssertionError("code explanation must not persist memory")
        ),
    )

    result = code_understanding.explain_file(
        "README.md",
        model="legacy-model-override",
    )

    assert result == private_response
    assert captured["model"] == "canonical-code-model"
    assert captured["temperature"] == 0.45
    assert "num_predict" not in captured
    assert private_source in captured["prompt"]

    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["agent_name"] == "code_agent"
    assert records[0]["model"] == "canonical-code-model"
    assert records[0]["status"] == "success"
    assert records[0]["duration_ms"] == 12
    assert records[0]["memory_persisted"] is False

    serialized_audit = audit_path.read_text(encoding="utf-8")
    assert private_source not in serialized_audit
    assert private_response not in serialized_audit
    assert captured["prompt"] not in serialized_audit

    evaluation = runtime_evaluation.evaluate_runtime(audit_path)
    assert evaluation["total_executions"] == 1
    assert evaluation["success_count"] == 1


def test_code_explanation_preserves_deterministic_model_error(
    tmp_path,
    monkeypatch,
):
    audit_path = tmp_path / "runtime.log"
    timeout_response = "Ollama request timed out. Is the local model overloaded?"

    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", audit_path)
    monkeypatch.setattr(
        code_understanding,
        "read_file",
        lambda path: "source",
    )
    monkeypatch.setattr(
        code_understanding,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-code-model",
            "temperature": 0.2,
        },
    )
    monkeypatch.setattr(
        code_understanding,
        "execute_model",
        lambda **kwargs: ModelExecutionResult(
            timeout_response,
            "timeout",
            9,
            "ollama_timeout",
        ),
    )

    assert code_understanding.explain_file("README.md") == timeout_response

    record = json.loads(audit_path.read_text(encoding="utf-8"))
    assert record["status"] == "timeout"
    assert record["error_category"] == "ollama_timeout"


def test_audit_write_failure_does_not_break_code_explanation(monkeypatch):
    monkeypatch.setattr(
        code_understanding,
        "read_file",
        lambda path: "source",
    )
    monkeypatch.setattr(
        code_understanding,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-code-model",
            "temperature": 0.2,
        },
    )
    monkeypatch.setattr(
        code_understanding,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )

    def fail_open(*args, **kwargs):
        raise OSError("read only")

    monkeypatch.setattr(audit_log.Path, "open", fail_open)

    assert code_understanding.explain_file("README.md") == "answer"


def test_existing_permissions_still_gate_explanation(monkeypatch):
    handler_called = False

    def fake_handler(args):
        nonlocal handler_called
        handler_called = True
        return "explained"

    monkeypatch.setitem(command_registry.COMMANDS, "/explain", fake_handler)
    monkeypatch.setattr(
        tool_router,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-model",
            "allowed_tools": [],
        },
    )

    result = tool_router.route_tool(
        "/explain README.md",
        FakeMemory(),
        agent_name="research_agent",
    )

    assert result == "Tool not allowed for agent: research_agent"
    assert handler_called is False
