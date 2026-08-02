from app import chat, cli


class FakeMemory:
    def __init__(self, name):
        self.name = name

    def load(self):
        pass

    def latest_user_fact(self):
        return None


class FakeRenderer:
    callbacks = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def update(self, event):
        self.callbacks.append(event)


def test_mentor_cli_final_response_is_unchanged(monkeypatch, capsys):
    answers = iter(["question", "/bye"])
    captured = {}
    monkeypatch.setattr(cli, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(cli, "CLIStatusRenderer", FakeRenderer)
    monkeypatch.setattr(cli, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(cli, "route_tool", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "classify", lambda question: cli.InputType.AI_REQUEST)

    def fake_ask(question, memory, on_status=None):
        captured["callback"] = on_status
        return "unchanged answer"

    monkeypatch.setattr(cli, "ask_mentor", fake_ask)

    cli.run_mentor_chat()

    assert "STS Mentor: unchanged answer" in capsys.readouterr().out
    assert captured["callback"] is not None


def test_generic_chat_commands_remain_compatible(monkeypatch, capsys):
    answers = iter(["/tools", "/bye"])
    monkeypatch.setattr(chat, "list_agents", lambda: ["code_agent"])
    monkeypatch.setattr(chat, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(chat, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(
        chat,
        "route_tool",
        lambda command, memory, agent_name: "available tools" if command == "/tools" else None,
    )

    chat.start_chat("code_agent")

    output = capsys.readouterr().out
    assert "available tools" in output
    assert "Goodbye." in output
