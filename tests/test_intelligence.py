import ast
import json
from pathlib import Path

import pytest

from app import agent_runtime, audit_log, intelligence, memory as memory_module
from app.agent_runtime import AgentRuntimeResult
from app.intelligence import (
    IntelligenceContext,
    IntelligenceRequest,
    invoke_intelligence,
)
from app.model_execution import ModelExecutionResult


def request(**overrides):
    values = {
        "agent_name": "code_agent",
        "user_input": "Explain the module",
        "consumer_id": "engineering-client",
        "session_id": "session-1",
    }
    values.update(overrides)
    return IntelligenceRequest(**values)


def fake_runtime_result(
    status="success",
    response="answer",
    memory_persisted=False,
    error_category=None,
):
    return AgentRuntimeResult(
        response=response,
        status=status,
        model="canonical-model",
        memory_persisted=memory_persisted,
        error_category=error_category,
    )


@pytest.fixture
def isolated_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_module, "MEMORY_DIR", tmp_path / "memory")
    return tmp_path / "memory"


def test_successful_public_invocation_returns_structured_response(
    isolated_memory,
    monkeypatch,
):
    captured = {}

    def fake_execute(**kwargs):
        captured.update(kwargs)
        return fake_runtime_result()

    monkeypatch.setattr(intelligence, "execute_agent_result", fake_execute)

    response = invoke_intelligence(request())

    assert response.status == "success"
    assert response.content == "answer"
    assert response.agent_name == "code_agent"
    assert response.model == "canonical-model"
    assert response.memory_persisted is False
    assert response.error_category is None
    assert captured["agent_name"] == "code_agent"


def test_internal_failure_returns_structured_failure(monkeypatch):
    class FailingMemory:
        def __init__(self, name):
            pass

        def load(self):
            raise OSError("private storage detail")

    monkeypatch.setattr(intelligence, "ConversationMemory", FailingMemory)

    response = invoke_intelligence(request())

    assert response.status == "failure"
    assert response.content == "Intelligence request failed."
    assert response.error_category == "runtime_error"
    assert "private storage detail" not in response.content


def test_boundary_uses_canonical_agent_configuration(
    isolated_memory,
    monkeypatch,
):
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    captured = {}

    def fake_execute_model(**kwargs):
        captured.update(kwargs)
        return ModelExecutionResult("answer", "success", 1)

    monkeypatch.setattr(agent_runtime, "execute_model", fake_execute_model)

    response = invoke_intelligence(request())

    assert response.status == "success"
    assert response.model == "sts-fast"
    assert captured["model"] == "sts-fast"
    assert captured["temperature"] == 0.2


@pytest.mark.parametrize(
    ("overrides", "error_category"),
    [
        ({"agent_name": "missing_agent"}, "unknown_agent"),
        ({"consumer_id": ""}, "invalid_consumer_id"),
        ({"consumer_id": "../consumer"}, "invalid_consumer_id"),
        ({"session_id": ""}, "invalid_session_id"),
        ({"session_id": "../session"}, "invalid_session_id"),
        ({"user_input": "  "}, "invalid_user_input"),
        ({"persistence": "sometimes"}, "invalid_persistence_policy"),
    ],
)
def test_invalid_requests_do_not_invoke_runtime(
    monkeypatch,
    overrides,
    error_category,
):
    def unexpected_execute(**kwargs):
        raise AssertionError("runtime must not be invoked")

    monkeypatch.setattr(intelligence, "execute_agent_result", unexpected_execute)

    response = invoke_intelligence(request(**overrides))

    assert response.status == "invalid_request"
    assert response.error_category == error_category
    assert response.memory_persisted is False


def test_caller_context_size_is_bounded(monkeypatch):
    monkeypatch.setattr(intelligence, "MAX_CALLER_CONTEXT_CHARS", 4)
    monkeypatch.setattr(
        intelligence,
        "execute_agent_result",
        lambda **kwargs: pytest.fail("runtime must not be invoked"),
    )

    response = invoke_intelligence(
        request(context=IntelligenceContext("12345"))
    )

    assert response.status == "invalid_request"
    assert response.error_category == "caller_context_too_large"


def test_ephemeral_context_reaches_prompt_but_is_not_persisted(
    isolated_memory,
    monkeypatch,
):
    captured = {}
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "build_prompt",
        lambda **kwargs: captured.update(kwargs) or "prompt",
    )
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )

    response = invoke_intelligence(
        request(context=IntelligenceContext("temporary product facts"))
    )

    assert response.status == "success"
    assert response.memory_persisted is False
    assert "temporary product facts" in captured["conversation"]
    assert not isolated_memory.exists()


def test_explicit_persistence_saves_exactly_once(monkeypatch):
    calls = {"load": 0, "save": 0}

    class FakeMemory:
        def __init__(self, name):
            self.name = name
            self.messages = []

        def load(self):
            calls["load"] += 1

        def context(self):
            return ""

        def add(self, role, content):
            self.messages.append((role, content))

        def save(self):
            calls["save"] += 1

    monkeypatch.setattr(intelligence, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )

    response = invoke_intelligence(request(persistence="persist"))

    assert response.status == "success"
    assert response.memory_persisted is True
    assert calls == {"load": 1, "save": 1}


@pytest.mark.parametrize(
    ("status", "error_category"),
    [
        ("failure", "ollama_error"),
        ("timeout", "ollama_timeout"),
    ],
)
def test_unsuccessful_execution_does_not_persist(
    monkeypatch,
    status,
    error_category,
):
    captured = {}

    class FakeMemory:
        def __init__(self, name):
            pass

        def load(self):
            pass

        def context(self):
            return ""

        def add(self, role, content):
            captured.setdefault("messages", []).append((role, content))

        def save(self):
            captured["save"] = True

    monkeypatch.setattr(intelligence, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult(
            "model unavailable",
            status,
            1,
            error_category,
        ),
    )

    response = invoke_intelligence(request(persistence="persist"))

    assert response.status == status
    assert response.error_category == error_category
    assert response.memory_persisted is False
    assert captured == {}


def test_consumer_and_session_memory_scopes_are_isolated(monkeypatch):
    names = []

    class FakeMemory:
        def __init__(self, name):
            names.append(name)

        def load(self):
            pass

    monkeypatch.setattr(intelligence, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(
        intelligence,
        "execute_agent_result",
        lambda **kwargs: fake_runtime_result(),
    )

    invoke_intelligence(request(consumer_id="consumer-a", session_id="shared"))
    invoke_intelligence(request(consumer_id="consumer-b", session_id="shared"))
    invoke_intelligence(request(consumer_id="consumer-a", session_id="other"))

    assert len(set(names)) == 3
    assert all(name.startswith("intelligence_") for name in names)
    assert all("consumer" not in name and "shared" not in name for name in names)


def test_audit_excludes_user_input_and_caller_context(
    tmp_path,
    isolated_memory,
    monkeypatch,
):
    audit_path = tmp_path / "runtime.log"
    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", audit_path)
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult(
            "private model response",
            "success",
            1,
        ),
    )

    invoke_intelligence(
        request(
            user_input="private user input",
            context=IntelligenceContext("private caller context"),
        )
    )

    serialized = audit_path.read_text(encoding="utf-8")
    record = json.loads(serialized)
    assert record["memory_persisted"] is False
    assert "private user input" not in serialized
    assert "private caller context" not in serialized
    assert "private model response" not in serialized


def test_boundary_is_product_neutral(isolated_memory, monkeypatch):
    monkeypatch.setattr(
        intelligence,
        "execute_agent_result",
        lambda **kwargs: fake_runtime_result(),
    )

    response = invoke_intelligence(
        request(
            consumer_id="future-product",
            context=IntelligenceContext("domain-neutral facts"),
        )
    )

    assert response.status == "success"


def test_public_boundary_does_not_import_or_call_raw_ollama():
    path = Path("app/intelligence.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "app.ollama_client" not in imported_modules
    assert "run_ollama" not in called_names


def test_existing_execute_agent_still_returns_string(monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: {
            "model": "canonical-model",
            "temperature": 0.2,
            "description": "",
            "prompt_text": "prompt",
        },
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )

    class FakeMemory:
        def context(self):
            return ""

        def add(self, role, content):
            pass

        def save(self):
            pass

    assert agent_runtime.execute_agent(
        "code_agent",
        "question",
        FakeMemory(),
    ) == "answer"


def test_intelligence_caller_emits_no_terminal_output(
    isolated_memory,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        intelligence,
        "execute_agent_result",
        lambda **kwargs: fake_runtime_result(),
    )

    response = invoke_intelligence(request())

    assert response.content == "answer"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
