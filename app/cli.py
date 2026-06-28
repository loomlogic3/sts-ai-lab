import sys

from app.mentor import ask_mentor


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli mentor")
        return

    command = sys.argv[1]

    if command == "mentor":
        question = input("Ask STS Mentor: ")
        answer = ask_mentor(question)
        print()
        print(answer)
        return

    print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
