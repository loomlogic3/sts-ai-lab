from app.agent_config import load_agent_definition, list_agent_definitions
from app.command_registry import get_handler, list_registered_commands
from app.tool_router import route_tool, tool_allowed


class FakeMemory:
    def __init__(self):
        self.messages = ["User: remembered fact"]
        self.clear_calls = 0

    def context(self):
        return "\n".join(self.messages)

    def clear(self):
        self.clear_calls += 1
        self.messages = []


def test_permissions_load_from_canonical_agent_definitions():
    code_agent = load_agent_definition("code_agent")

    assert "/read" in code_agent["allowed_tools"]
    assert "/analyze" in code_agent["allowed_tools"]
    assert "/knowledge" not in code_agent["allowed_tools"]


def test_existing_agent_definitions_have_valid_registered_permissions():
    registered_commands = set(list_registered_commands())

    for definition in list_agent_definitions():
        assert definition["allowed_tools"]
        assert set(definition["allowed_tools"]).issubset(registered_commands)


def test_allowed_registered_tool_executes_for_agent():
    result = route_tool("/knowledge STS", FakeMemory(), agent_name="research_agent")

    assert result != "Tool not allowed for agent: research_agent"
    assert result is not None


def test_blocked_registered_tool_returns_deterministic_message():
    result = route_tool("/analyze app/cli.py", FakeMemory(), agent_name="research_agent")

    assert result == "Tool not allowed for agent: research_agent"


def test_unknown_command_still_returns_none_for_ai_fallthrough():
    result = route_tool("/not-a-real-command hello", FakeMemory(), agent_name="code_agent")

    assert result is None


def test_memory_command_still_uses_active_memory_object():
    memory = FakeMemory()

    assert route_tool("/memory", memory, agent_name="research_agent") == "User: remembered fact"


def test_clear_command_still_uses_active_memory_object():
    memory = FakeMemory()

    assert route_tool("/clear", memory, agent_name="research_agent") == "Memory cleared."
    assert memory.clear_calls == 1
    assert memory.messages == []


def test_registered_command_lookup_remains_intact():
    assert get_handler("/read") is not None
    assert get_handler("/knowledge") is not None
    assert get_handler("/memory") is None
    assert get_handler("/clear") is None


def test_tool_allowed_defaults_to_true_without_active_agent():
    assert tool_allowed(None, "/analyze") is True
