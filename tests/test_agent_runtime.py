from app import agent_runtime, ai_engine, mentor
from app.agent_runtime import AgentRuntimeOptions


class FakeMemory:
    def __init__(self, context=""):
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
        "temperature": 0.35,
        "description": "Canonical description",
        "prompt_text": "Canonical prompt",
    }


def test_generic_agent_execution_uses_canonical_runtime(monkeypatch):
    captured = {}

    def fake_execute(agent_name, question, memory, options):
        captured["call"] = (agent_name, question, memory, options)
        return "answer"

    monkeypatch.setattr(ai_engine, "execute_agent", fake_execute)
    memory = FakeMemory()

    assert ai_engine.answer_with_agent("code_agent", "hello", memory) == "answer"
    assert captured["call"][:3] == ("code_agent", "hello", memory)
    assert captured["call"][3].include_agent_config is True


def test_mentor_execution_uses_canonical_runtime(monkeypatch):
    captured = {}

    def fake_execute(agent_name, question, memory, options):
        captured["call"] = (agent_name, question, memory, options)
        return "answer"

    monkeypatch.setattr(mentor, "execute_agent", fake_execute)
    memory = FakeMemory()

    assert mentor.ask_mentor("hello", memory) == "answer"
    assert captured["call"][:3] == ("sts_mentor", "hello", memory)
    assert captured["call"][3].memory_role == "STS Mentor"
    assert captured["call"][3].knowledge_chars == mentor.MAX_MENTOR_KNOWLEDGE_CHARS
    assert captured["call"][3].num_predict == mentor.MENTOR_NUM_PREDICT


def test_canonical_definition_supplies_runtime_metadata(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")

    def fake_build_prompt(**kwargs):
        captured["prompt_parts"] = kwargs
        return "built prompt"

    monkeypatch.setattr(agent_runtime, "build_prompt", fake_build_prompt)

    def fake_run(model, prompt, **kwargs):
        captured["ollama"] = (model, prompt, kwargs)
        return "answer"

    monkeypatch.setattr(agent_runtime, "run_ollama", fake_run)

    agent_runtime.execute_agent(
        "code_agent",
        "hello",
        FakeMemory(),
        AgentRuntimeOptions(include_agent_config=True),
    )

    assert captured["prompt_parts"]["system_prompt"] == "Canonical prompt"
    assert "Canonical description" in captured["prompt_parts"]["conversation"]
    assert captured["ollama"] == (
        "canonical-model",
        "built prompt",
        {"temperature": 0.35},
    )


def test_conversation_and_knowledge_budgets_remain_enforced(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(agent_runtime, "MAX_CONVERSATION_CHARS", 4)
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "knowledge")
    monkeypatch.setattr(
        agent_runtime,
        "build_prompt",
        lambda **kwargs: captured.update(kwargs) or "prompt",
    )
    monkeypatch.setattr(agent_runtime, "run_ollama", lambda *args, **kwargs: "answer")

    agent_runtime.execute_agent(
        "sts_mentor",
        "hello",
        FakeMemory("conversation"),
        AgentRuntimeOptions(knowledge_chars=3),
    )

    assert captured["conversation"] == "tion"
    assert captured["knowledge"] == "kno"


def test_successful_answer_persists_memory_exactly_once(monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(agent_runtime, "run_ollama", lambda *args, **kwargs: " answer ")
    memory = FakeMemory()

    answer = agent_runtime.execute_agent("code_agent", "hello", memory)

    assert answer == "answer"
    assert memory.messages == [
        ("User", "hello"),
        ("code_agent", "answer"),
    ]
    assert memory.save_calls == 1


def test_failed_ollama_response_is_not_persisted(monkeypatch):
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "run_ollama",
        lambda *args, **kwargs: "Ollama connection failed: refused",
    )
    memory = FakeMemory()

    answer = agent_runtime.execute_agent("code_agent", "hello", memory)

    assert answer == "Ollama connection failed: refused"
    assert memory.messages == []
    assert memory.save_calls == 0


def test_mentor_output_limit_and_memory_role_remain_intact(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")

    def fake_run(model, prompt, **kwargs):
        captured.update(kwargs)
        return "answer"

    monkeypatch.setattr(agent_runtime, "run_ollama", fake_run)
    memory = FakeMemory()

    mentor.ask_mentor("hello", memory)

    assert captured["num_predict"] == mentor.MENTOR_NUM_PREDICT
    assert memory.messages[-1] == ("STS Mentor", "answer")
