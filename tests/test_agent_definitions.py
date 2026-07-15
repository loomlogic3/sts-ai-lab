from app.agent_config import load_agent_definition, list_agent_definitions, list_agent_names
from app.agent_registry import list_agents, load_agent_prompt
from app.agents import list_agents as list_agent_summaries


def test_agent_names_come_from_canonical_json_definitions():
    assert list_agent_names() == [
        "code_agent",
        "research_agent",
        "sts_mentor",
    ]
    assert list_agents() == list_agent_names()


def test_agent_definition_includes_existing_metadata_and_prompt():
    definition = load_agent_definition("code_agent")

    assert definition["name"] == "code_agent"
    assert definition["prompt"] == "code_agent.md"
    assert definition["model"] == "sts-fast"
    assert definition["temperature"] == 0.2
    assert "Python" in definition["description"]
    assert definition["prompt_text"]


def test_load_agent_prompt_uses_canonical_definition():
    definition = load_agent_definition("sts_mentor")

    assert load_agent_prompt("sts_mentor") == definition["prompt_text"]


def test_agent_summaries_use_canonical_definitions():
    summaries = list_agent_summaries()
    names = [agent["name"] for agent in summaries]

    assert names == list_agent_names()
    assert all(agent["model"] == "sts-fast" for agent in summaries)


def test_all_agent_definitions_include_prompt_files():
    definitions = list_agent_definitions()

    assert len(definitions) == 3
    assert all(definition["prompt"].endswith(".md") for definition in definitions)
