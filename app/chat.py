"""
Generic chat runner for all STS AI agents.
"""

from app.agent_registry import list_agents, load_agent_prompt
from app.config import DEFAULT_MODEL
from app.input_classifier import InputType, classify
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.ollama_client import run_ollama
from app.prompt_builder import build_prompt
from app.response_processor import clean_response
from app.tool_router import route_tool


def ask_agent(agent_name: str, question: str, memory: ConversationMemory) -> str:
    """
    Ask any registered STS AI agent a question.
    """

    system_prompt = load_agent_prompt(agent_name)
    conversation_context = memory.context()
    knowledge = search_knowledge(question)

    full_prompt = build_prompt(
        system_prompt=system_prompt,
        conversation=conversation_context,
        user_question=question,
        knowledge=knowledge,
    )

    raw_answer = run_ollama(DEFAULT_MODEL, full_prompt)
    answer = clean_response(raw_answer)

    memory.add("User", question)
    memory.add(agent_name, answer)
    memory.save()

    return answer


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

    memory = ConversationMemory()
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

        input_type = classify(question)

        if input_type == InputType.STATEMENT:
            memory.add("User", question)
            memory.save()
            print()
            print(f"{agent_name}: Noted. I'll remember that during this session.")
            print()
            continue

        answer = ask_agent(agent_name, question, memory)

        print()
        print(f"{agent_name}: {answer}")
        print()
