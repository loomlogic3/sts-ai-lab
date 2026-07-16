from app import agent_runtime, ai_engine, mentor
from app.ollama_client import is_ollama_error


class FakeMemory:
    def __init__(self):
        self.messages = []
        self.save_calls = 0

    def context(self):
        return ""

    def add(self, role, content):
        self.messages.append(f"{role}: {content}")

    def save(self):
        self.save_calls += 1


def test_ollama_timeout_is_recognized_as_error():
    assert is_ollama_error(
        "Ollama request timed out. Is the local model overloaded?"
    )


def test_generic_agent_does_not_save_ollama_error(monkeypatch):
    memory = FakeMemory()

    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: {
            "model": "sts-fast",
            "temperature": 0.2,
            "description": "",
            "prompt_text": "prompt",
        },
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "run_ollama",
        lambda *args, **kwargs: (
            "Ollama request timed out. Is the local model overloaded?"
        ),
    )

    answer = ai_engine.answer_with_agent(
        "code_agent",
        "hello",
        memory,
    )

    assert answer.startswith("Ollama request timed out.")
    assert memory.messages == []
    assert memory.save_calls == 0


def test_mentor_does_not_save_ollama_error(monkeypatch):
    memory = FakeMemory()

    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: {
            "model": "sts-fast",
            "temperature": 0.2,
            "description": "",
            "prompt_text": "prompt",
        },
    )
    monkeypatch.setattr(agent_runtime, "search_knowledge", lambda question: "")
    monkeypatch.setattr(
        agent_runtime,
        "run_ollama",
        lambda *args, **kwargs: (
            "Ollama connection failed: Connection refused"
        ),
    )

    answer = mentor.ask_mentor("hello", memory)

    assert answer.startswith("Ollama connection failed:")
    assert memory.messages == []
    assert memory.save_calls == 0
