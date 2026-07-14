import inspect

from app import command_registry, tool_router
from app.command_registry import get_handler, list_registered_commands
from app.tool_registry import format_tools, list_tools
from app.tool_router import route_tool


class FakeMemory:
    def __init__(self):
        self.messages = ["User: remembered fact"]
        self.clear_calls = 0

    def context(self):
        return "\n".join(self.messages)

    def clear(self):
        self.clear_calls += 1
        self.messages = []


def test_tool_commands_are_registered_except_stateful_memory_commands():
    stateful_commands = {"/memory", "/clear"}

    for tool in list_tools():
        command_name = tool["command"].split()[0]

        if command_name in stateful_commands:
            continue

        assert get_handler(command_name) is not None, command_name


def test_registered_read_command_dispatches_through_router():
    result = route_tool("/read README.md", FakeMemory())

    assert "# sts-ai-lab" in result


def test_registered_command_receives_arguments(monkeypatch):
    captured = {}

    def fake_handler(args):
        captured["args"] = args
        return f"handled {args}"

    monkeypatch.setitem(command_registry.COMMANDS, "/__test", fake_handler)

    result = route_tool("/__test alpha beta", FakeMemory())

    assert result == "handled alpha beta"
    assert captured["args"] == "alpha beta"


def test_unknown_command_returns_none_for_ai_fallthrough():
    assert route_tool("/not-a-command hello", FakeMemory()) is None


def test_memory_command_uses_active_memory_object():
    memory = FakeMemory()

    assert route_tool("/memory", memory) == "User: remembered fact"


def test_clear_command_uses_active_memory_object():
    memory = FakeMemory()

    assert route_tool("/clear", memory) == "Memory cleared."
    assert memory.clear_calls == 1
    assert memory.messages == []


def test_stateful_commands_are_not_registered():
    assert get_handler("/memory") is None
    assert get_handler("/clear") is None


def test_router_no_longer_contains_duplicate_stateless_branches():
    source = inspect.getsource(tool_router.route_tool)

    removed_branches = [
        'command.startswith("/search ")',
        'command.startswith("/grep ")',
        'command == "/todos"',
        'command.startswith("/plan-change ")',
        'command.startswith("/risk ")',
        'command.startswith("/proposal ")',
        'command.startswith("/propose-patch ")',
        'command.startswith("/draft-patch ")',
        'command.startswith("/approval-required ")',
        'command.startswith("/design ")',
        'command.startswith("/read ")',
        'command.startswith("/explain ")',
        'command.startswith("/analyze ")',
        'command.startswith("/functions ")',
        'command.startswith("/classes ")',
        'command.startswith("/imports ")',
        'command == "/index"',
        'command == "/project-map"',
        'command.startswith("/where ")',
        'command == "/experiments"',
        'command.startswith("/knowledge ")',
        'command.startswith("/log ")',
    ]

    for branch in removed_branches:
        assert branch not in source


def test_tools_output_still_lists_expected_commands():
    output = format_tools()

    expected_commands = [
        "/memory",
        "/clear",
        "/knowledge <query>",
        "/read <file_path>",
        "/tree",
        "/search <keyword>",
        "/grep <keyword>",
        "/tools",
    ]

    for command in expected_commands:
        assert command in output


def test_registered_commands_are_sorted():
    commands = list_registered_commands()

    assert commands == sorted(commands)
