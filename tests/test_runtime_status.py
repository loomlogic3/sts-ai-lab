import ast
from dataclasses import asdict
from pathlib import Path

import pytest

from app import agent_runtime
from app.agent_runtime import AgentRuntimeOptions
from app.model_execution import ModelExecutionResult


class FakeMemory:
    def __init__(self, context="private conversation"):
        self.context_text = context

    def context(self):
        return self.context_text

    def add(self, role, content):
        pass

    def save(self):
        pass


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-model",
            "temperature": 0.2,
            "description": "description",
            "prompt_text": "private system prompt",
        },
    )
    monkeypatch.setattr(
        agent_runtime,
        "search_knowledge",
        lambda question: "private knowledge",
    )


def test_runtime_emits_truthful_statuses_in_order(runtime, monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("private response", "success", 1),
    )
    events = []

    result = agent_runtime.execute_agent_result(
        "code_agent",
        "private user input",
        FakeMemory(),
        on_status=events.append,
    )

    assert result.response == "private response"
    assert [event.stage for event in events] == [
        "loading_agent",
        "reading_memory",
        "searching_knowledge",
        "building_prompt",
        "waiting_for_model",
        "processing_response",
        "saving_memory",
        "complete",
    ]


def test_ephemeral_runtime_omits_saving_memory_status(runtime, monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )
    events = []

    agent_runtime.execute_agent_result(
        "code_agent",
        "question",
        FakeMemory(),
        AgentRuntimeOptions(persist_memory=False),
        on_status=events.append,
    )

    assert "saving_memory" not in [event.stage for event in events]


@pytest.mark.parametrize(
    ("status", "terminal_stage"),
    [("timeout", "timeout"), ("failure", "failure")],
)
def test_runtime_emits_model_terminal_status(
    runtime,
    monkeypatch,
    status,
    terminal_stage,
):
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("unchanged error", status, 1, "error"),
    )
    events = []

    result = agent_runtime.execute_agent_result(
        "code_agent",
        "question",
        FakeMemory(),
        on_status=events.append,
    )

    assert result.response == "unchanged error"
    assert events[-1].stage == terminal_stage


def test_runtime_emits_failure_when_processing_raises(runtime, monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )
    monkeypatch.setattr(
        agent_runtime,
        "clean_response",
        lambda response: (_ for _ in ()).throw(ValueError("bad response")),
    )
    events = []

    with pytest.raises(ValueError, match="bad response"):
        agent_runtime.execute_agent_result(
            "code_agent",
            "question",
            FakeMemory(),
            on_status=events.append,
        )

    assert events[-1].stage == "failure"


def test_runtime_emits_failure_when_agent_loading_raises(monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: (_ for _ in ()).throw(ValueError("bad agent")),
    )
    events = []

    with pytest.raises(ValueError, match="bad agent"):
        agent_runtime.execute_agent_result(
            "code_agent",
            "question",
            FakeMemory(),
            on_status=events.append,
        )

    assert [event.stage for event in events] == ["loading_agent", "failure"]
    assert events[-1].model is None


def test_callback_failure_does_not_break_execution(runtime, monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )

    def broken_callback(event):
        raise RuntimeError("presentation failed")

    assert agent_runtime.execute_agent(
        "code_agent",
        "question",
        FakeMemory(),
        on_status=broken_callback,
    ) == "answer"


def test_status_events_contain_control_metadata_only(runtime, monkeypatch):
    secrets = (
        "private user input",
        "private system prompt",
        "private conversation",
        "private knowledge",
        "private response",
    )
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult(secrets[-1], "success", 1),
    )
    events = []

    agent_runtime.execute_agent_result(
        "code_agent",
        secrets[0],
        FakeMemory(),
        on_status=events.append,
    )

    serialized = repr([asdict(event) for event in events])
    assert all(secret not in serialized for secret in secrets)
    assert set(asdict(events[-1])) == {"stage", "agent_name", "model"}


def test_runtime_modules_contain_no_terminal_rendering_code():
    forbidden_imports = {"threading", "rich"}
    for filename in ("agent_runtime.py", "model_execution.py"):
        source = Path("app", filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert imports.isdisjoint(forbidden_imports)
        assert "\\x1b" not in source
        assert "\\r" not in source
