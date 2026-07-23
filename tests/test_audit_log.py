import json

import pytest

from app import agent_runtime, audit_log, tool_router


class FakeMemory:
    def __init__(self, context="private conversation"):
        self.context_text = context
        self.messages = []
        self.save_calls = 0

    def context(self):
        return self.context_text

    def add(self, role, content):
        self.messages.append((role, content))

    def save(self):
        self.save_calls += 1


def agent_definition():
    return {
        "model": "canonical-model",
        "temperature": 0.2,
        "description": "description",
        "prompt_text": "private prompt",
    }


@pytest.fixture
def audit_path(tmp_path, monkeypatch):
    path = tmp_path / "runtime.jsonl"
    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", path)
    return path


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(
        agent_runtime,
        "search_knowledge",
        lambda question: "private knowledge",
    )


def read_records(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def test_successful_execution_writes_one_private_audit_record(
    audit_path,
    runtime,
    monkeypatch,
):
    monkeypatch.setattr(
        agent_runtime,
        "run_ollama",
        lambda *args, **kwargs: "private response",
    )
    memory = FakeMemory()

    answer = agent_runtime.execute_agent(
        "code_agent",
        "private user question",
        memory,
    )

    records = read_records(audit_path)
    assert answer == "private response"
    assert len(records) == 1
    assert records[0]["agent_name"] == "code_agent"
    assert records[0]["model"] == "canonical-model"
    assert records[0]["status"] == "success"
    assert records[0]["memory_persisted"] is True
    assert records[0]["error_category"] is None
    assert records[0]["timestamp"].endswith("+00:00")
    assert isinstance(records[0]["duration_ms"], int)

    serialized = audit_path.read_text(encoding="utf-8")
    for private_value in (
        "private prompt",
        "private user question",
        "private conversation",
        "private knowledge",
        "private response",
    ):
        assert private_value not in serialized


@pytest.mark.parametrize(
    ("ollama_response", "status", "error_category"),
    [
        (
            "Ollama request timed out. Is the local model overloaded?",
            "timeout",
            "ollama_timeout",
        ),
        (
            "Ollama connection failed: refused",
            "failure",
            "ollama_error",
        ),
    ],
)
def test_ollama_errors_write_the_correct_outcome(
    audit_path,
    runtime,
    monkeypatch,
    ollama_response,
    status,
    error_category,
):
    monkeypatch.setattr(
        agent_runtime,
        "run_ollama",
        lambda *args, **kwargs: ollama_response,
    )
    memory = FakeMemory()

    assert agent_runtime.execute_agent("code_agent", "question", memory) == ollama_response

    record = read_records(audit_path)[0]
    assert record["status"] == status
    assert record["memory_persisted"] is False
    assert record["error_category"] == error_category
    assert memory.save_calls == 0


def test_memory_save_failure_is_audited_and_preserves_exception(
    audit_path,
    runtime,
    monkeypatch,
):
    monkeypatch.setattr(agent_runtime, "run_ollama", lambda *args, **kwargs: "answer")
    memory = FakeMemory()

    def fail_save():
        raise OSError("disk full")

    memory.save = fail_save

    with pytest.raises(OSError, match="disk full"):
        agent_runtime.execute_agent("code_agent", "question", memory)

    record = read_records(audit_path)[0]
    assert record["status"] == "failure"
    assert record["memory_persisted"] is False
    assert record["error_category"] == "runtime_error"


def test_blocked_tool_execution_writes_blocked_outcome(
    audit_path,
    monkeypatch,
):
    monkeypatch.setattr(
        tool_router,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-model",
            "allowed_tools": [],
        },
    )

    result = tool_router.route_tool(
        "/knowledge private arguments",
        FakeMemory(),
        agent_name="code_agent",
    )

    assert result == "Tool not allowed for agent: code_agent"
    record = read_records(audit_path)[0]
    assert record["status"] == "blocked"
    assert record["memory_persisted"] is False
    assert record["error_category"] == "tool_not_allowed"
    assert "private arguments" not in audit_path.read_text(encoding="utf-8")


def test_audit_write_failure_does_not_break_agent_response(runtime, monkeypatch):
    monkeypatch.setattr(agent_runtime, "run_ollama", lambda *args, **kwargs: "answer")

    def fail_open(*args, **kwargs):
        raise OSError("read only")

    monkeypatch.setattr(audit_log.Path, "open", fail_open)
    memory = FakeMemory()

    assert agent_runtime.execute_agent("code_agent", "question", memory) == "answer"
    assert memory.save_calls == 1
