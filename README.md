# sts-ai-lab
SynthThinkingSystems AI Research &amp; Engineering Laboratory

---

# STS AI Engine CLI

The STS AI Engine provides a modular command-line interface for the local AI Lab.

## Requirements

- Python 3.11+
- Ollama installed and running
- Llama 3.2 1B model downloaded

## Commands

Start STS Mentor:

    python3 -m app.cli mentor

View memory:

    python3 -m app.cli memory

Search knowledge:

    python3 -m app.cli knowledge "local AI stack"

Log an experiment:

    python3 -m app.cli experiment

View AI Lab status:

    python3 -m app.cli status

## In-session Mentor Commands

- /memory: show saved memory
- /clear: clear persistent memory
- /knowledge <query>: search the knowledge base
- /log <note>: save an experiment note
- /tools: list available tools
- /bye: exit the session

## Principle

Research first. Build second. Deploy third.

