import pytest

from app import chat, cli


class FakeMemory:
    def __init__(self, name):
        self.name = name
        self.messages = []
        self.save_calls = 0

    def load(self):
        pass

    def latest_user_fact(self):
        return None

    def add(self, role, content):
        self.messages.append((role, content))

    def save(self):
        self.save_calls += 1


class FakeRenderer:
    callbacks = []
    exits = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.exits.append(exc_type)

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


def test_mentor_request_cancellation_is_clean_and_loop_continues(
    monkeypatch,
    capsys,
):
    answers = iter(["cancel this", "try again", "/bye"])
    memory = FakeMemory("sts_mentor")
    calls = {"count": 0}
    FakeRenderer.exits = []
    monkeypatch.setattr(cli, "ConversationMemory", lambda name: memory)
    monkeypatch.setattr(cli, "CLIStatusRenderer", FakeRenderer)
    monkeypatch.setattr(cli, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(cli, "route_tool", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "classify", lambda question: cli.InputType.AI_REQUEST)

    def fake_ask(question, memory, on_status=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise KeyboardInterrupt
        return "completed answer"

    monkeypatch.setattr(cli, "ask_mentor", fake_ask)

    cli.run_mentor_chat()

    output = capsys.readouterr()
    assert "Request cancelled." in output.out
    assert "STS Mentor: completed answer" in output.out
    assert "Traceback" not in output.out + output.err
    assert memory.messages == []
    assert memory.save_calls == 0
    assert FakeRenderer.exits == [KeyboardInterrupt, None]


def test_repeated_mentor_cancellation_remains_usable(monkeypatch, capsys):
    answers = iter(["first", "second", "/bye"])
    FakeRenderer.exits = []
    monkeypatch.setattr(cli, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(cli, "CLIStatusRenderer", FakeRenderer)
    monkeypatch.setattr(cli, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(cli, "route_tool", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "classify", lambda question: cli.InputType.AI_REQUEST)
    monkeypatch.setattr(
        cli,
        "ask_mentor",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    cli.run_mentor_chat()

    assert capsys.readouterr().out.count("Request cancelled.") == 2
    assert FakeRenderer.exits == [KeyboardInterrupt, KeyboardInterrupt]


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


def test_generic_agent_request_cancellation_continues(monkeypatch, capsys):
    answers = iter(["question", "/bye"])
    FakeRenderer.exits = []
    monkeypatch.setattr(chat, "list_agents", lambda: ["code_agent"])
    monkeypatch.setattr(chat, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(chat, "CLIStatusRenderer", FakeRenderer)
    monkeypatch.setattr(chat, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(chat, "route_tool", lambda *args, **kwargs: None)
    monkeypatch.setattr(chat, "load_agent_definition", lambda name: {})
    monkeypatch.setattr(chat, "classify", lambda question: chat.InputType.AI_REQUEST)
    monkeypatch.setattr(
        chat,
        "answer_with_agent",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    chat.start_chat("code_agent")

    output = capsys.readouterr()
    assert "Request cancelled." in output.out
    assert "Goodbye." in output.out
    assert "Traceback" not in output.out + output.err
    assert FakeRenderer.exits == [KeyboardInterrupt]


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), EOFError()])
@pytest.mark.parametrize("runner", ["mentor", "generic"])
def test_plain_input_interruption_exits_cleanly(
    monkeypatch,
    capsys,
    runner,
    interruption,
):
    def interrupted_input(prompt):
        raise interruption

    if runner == "mentor":
        monkeypatch.setattr(cli, "ConversationMemory", FakeMemory)
        monkeypatch.setattr(cli, "input", interrupted_input, raising=False)
        cli.run_mentor_chat()
    else:
        monkeypatch.setattr(chat, "list_agents", lambda: ["code_agent"])
        monkeypatch.setattr(chat, "ConversationMemory", FakeMemory)
        monkeypatch.setattr(chat, "input", interrupted_input, raising=False)
        chat.start_chat("code_agent")

    output = capsys.readouterr()
    assert "Goodbye." in output.out
    assert "Traceback" not in output.out + output.err


@pytest.mark.parametrize(
    ("command", "result"),
    [("/clear", "Memory cleared."), ("/memory", "remembered fact")],
)
def test_mentor_memory_commands_remain_compatible(
    monkeypatch,
    capsys,
    command,
    result,
):
    answers = iter([command, "/bye"])
    monkeypatch.setattr(cli, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(cli, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(
        cli,
        "route_tool",
        lambda question, *args, **kwargs: result if question == command else None,
    )

    cli.run_mentor_chat()

    output = capsys.readouterr().out
    assert result in output
    assert "Goodbye." in output


@pytest.mark.parametrize(
    "response",
    [
        "Ollama request timed out. Is the local model overloaded?",
        "Ollama connection failed: refused",
        "successful answer",
    ],
)
def test_mentor_model_outcomes_remain_unchanged(
    monkeypatch,
    capsys,
    response,
):
    answers = iter(["question", "/bye"])
    monkeypatch.setattr(cli, "ConversationMemory", FakeMemory)
    monkeypatch.setattr(cli, "CLIStatusRenderer", FakeRenderer)
    monkeypatch.setattr(cli, "input", lambda prompt: next(answers), raising=False)
    monkeypatch.setattr(cli, "route_tool", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "classify", lambda question: cli.InputType.AI_REQUEST)
    monkeypatch.setattr(cli, "ask_mentor", lambda *args, **kwargs: response)

    cli.run_mentor_chat()

    assert f"STS Mentor: {response}" in capsys.readouterr().out
