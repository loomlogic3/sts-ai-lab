import sys

from app.agents import print_agents
from app.chat import start_chat
from app.experiment_logger import log_experiment
from app.experiments import print_experiments
from app.input_classifier import InputType, classify
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.models import print_models
from app.mentor import ask_mentor
from app.status import lab_status
from app.tool_registry import format_tools
from app.tool_router import route_tool
from app.project import project_summary


def run_mentor_chat() -> None:
    memory = ConversationMemory()
    memory.load()

    print("STS Mentor chat started.")
    print("Type /bye to exit.")
    print("Type /clear to clear memory.")
    print("Type /memory to show memory.")
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
            print("STS Mentor: Noted. I'll remember that during this session.")
            print()
            continue

        if input_type == InputType.QUESTION:
            latest_fact = memory.latest_user_fact()

            if latest_fact and "favorite language" in question.lower():
                print()
                print(f"STS Mentor: {latest_fact}")
                print()
                continue

            if latest_fact and "use locally" in question.lower():
                print()
                print(f"STS Mentor: {latest_fact}")
                print()
                continue

        answer = ask_mentor(question, memory)

        print()
        print(f"STS Mentor: {answer}")
        print()


def log_experiment_from_cli() -> None:
    title = input("Experiment title: ").strip()
    notes = input("Experiment notes: ").strip()

    if not title:
        print("Experiment title is required.")
        return

    if not notes:
        print("Experiment notes are required.")
        return

    path = log_experiment(title, notes)
    print(f"Experiment saved: {path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 -m app.cli mentor|chat|agents|models|experiment|experiments|memory|knowledge|tools|project|status")
        return

    command = sys.argv[1]

    if command == "mentor":
        run_mentor_chat()
        return

    if command == "chat":
        if len(sys.argv) < 3:
            print("Usage: python3 -m app.cli chat <agent_name>")
            return
        start_chat(sys.argv[2])
        return

    if command == "agents":
        print_agents()
        return

    if command == "experiment":
        log_experiment_from_cli()
        return

    if command == "experiments":
        print_experiments()
        return

    if command == "models":
        print_models()
        return

    if command == "memory":
        memory = ConversationMemory()
        memory.load()
        print(memory.context() or "No memory saved.")
        return

    if command == "knowledge":
        query = " ".join(sys.argv[2:]).strip()
        if not query:
            print("Usage: python3 -m app.cli knowledge <query>")
            return
        print(search_knowledge(query) or "No knowledge found.")
        return

    if command == "tools":
        print(format_tools())
        return

    if command == "project":
        print(project_summary())
        return

    if command == "status":
        print(lab_status())
        return

    print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
