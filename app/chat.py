"""
Generic chat runner for all STS AI agents.
"""
from app.agent_config import load_agent_definition

from app.agent_registry import list_agents
from app.ai_engine import answer_with_agent
from app.input_classifier import InputType, classify
from app.memory import ConversationMemory
from app.tool_router import route_tool


def start_chat(agent_name: str) -> None:
    """
    Start an interactive chat session with the selected agent.
    """

    if agent_name not in list_agents():
        print(f"Unknown agent: {agent_name}")
        print()
        print("Available agents:")

        for agent in list_agents():
            print(f" - {agent}")

        return

    memory = ConversationMemory(agent_name)
    memory.load()

    print(f"{agent_name} chat started.")
    print("Type /bye to exit.")
    print("Type /tools to list available tools.")
    print()

    while True:
        question = input("You: ")

        if not question.strip():
            continue

        if question.strip() == "/bye":
            print("Goodbye.")
            break

        tool_result = route_tool(question, memory)

        if tool_result is not None:
            print()
            print(tool_result)
            print()
            continue

        agent_definition = load_agent_definition(agent_name)

        if "what model" in question.lower() or "configured to use" in question.lower():
            print()
            print(f"{agent_name}: {agent_definition['model']}")
            print()
            continue

        capability_question = question.lower()

        if (
            "what kind of work" in capability_question
            or "what can you help" in capability_question
            or "what do you help" in capability_question
        ):
            print()
            print(f"{agent_name}: {agent_definition['description']}")
            print()
            continue

        input_type = classify(question)

        if input_type == InputType.STATEMENT:
            memory.add("User", question)
            memory.save()
            print()
            print(f"{agent_name}: Noted. I'll remember that during this session.")
            print()
            continue

        answer = answer_with_agent(agent_name, question, memory)

        print()
        print(f"{agent_name}: {answer}")
        print()
