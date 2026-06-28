import sys

from app.input_classifier import InputType, classify
from app.memory import ConversationMemory
from app.mentor import ask_mentor


def run_mentor_chat() -> None:
    memory = ConversationMemory()
    memory.load()

    print("STS Mentor chat started.")
    print("Type /bye to exit.")
    print("Type /clear to clear memory.")
    print()

    while True:
        question = input("You: ")

        if not question.strip():
            continue

        if question.strip() == "/bye":
            print("Goodbye.")
            break

        if question.strip() == "/clear":
            memory.clear()
            print("Memory cleared.")
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


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 -m app.cli mentor")
        return

    command = sys.argv[1]

    if command == "mentor":
        run_mentor_chat()
        return

    print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
