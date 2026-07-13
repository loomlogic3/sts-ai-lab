import json

from app import chat, cli
from app.memory import ConversationMemory, MAX_MEMORY_MESSAGES, safe_memory_name


def test_memory_keeps_recent_messages_only():
    memory = ConversationMemory()

    for index in range(MAX_MEMORY_MESSAGES + 5):
        memory.add("User", f"message {index}")

    assert len(memory.messages) == MAX_MEMORY_MESSAGES
    assert memory.messages[0] == "User: message 5"


def test_agent_memory_uses_agent_specific_file(tmp_path):
    memory = ConversationMemory("code_agent")
    memory.path = tmp_path / "memory" / "code_agent.json"
    memory.add("User", "hello")
    memory.save()

    loaded = ConversationMemory("code_agent")
    loaded.path = memory.path
    loaded.load()

    assert loaded.messages == ["User: hello"]


def test_default_memory_keeps_legacy_path_name():
    memory = ConversationMemory()
    assert str(memory.path) == "data/memory.json"


def test_safe_memory_name_blocks_path_like_names():
    assert safe_memory_name("../code agent") == "code_agent"
    assert safe_memory_name("") == "default"


def test_corrupt_memory_file_does_not_crash_load(tmp_path):
    memory_file = tmp_path / "broken.json"
    memory_file.write_text("{not valid json", encoding="utf-8")

    memory = ConversationMemory("broken")
    memory.path = memory_file
    memory.load()

    corrupt_file = memory_file.with_suffix(".corrupt.json")

    assert memory.messages == []
    assert corrupt_file.exists()


def test_memory_ignores_non_list_facts(tmp_path):
    memory_file = tmp_path / "memory.json"
    memory_file.write_text(json.dumps({"facts": "not a list"}), encoding="utf-8")

    memory = ConversationMemory()
    memory.path = memory_file
    memory.load()

    assert memory.messages == []


def test_mentor_chat_uses_mentor_memory(monkeypatch):
    captured = {}

    class FakeMemory:
        def __init__(self, name="default"):
            captured["name"] = name

        def load(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "ConversationMemory", FakeMemory)

    try:
        cli.run_mentor_chat()
    except KeyboardInterrupt:
        pass

    assert captured["name"] == "sts_mentor"


def test_generic_chat_uses_agent_memory(monkeypatch):
    captured = {}

    class FakeMemory:
        def __init__(self, name="default"):
            captured["name"] = name

        def load(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(chat, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(chat, "list_agents", lambda: ["code_agent"])

    try:
        chat.start_chat("code_agent")
    except KeyboardInterrupt:
        pass

    assert captured["name"] == "code_agent"
