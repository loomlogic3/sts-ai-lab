# sts-ai-lab
SynthThinkingSystems AI Research & Engineering Laboratory

A controlled, local-first AI engine and agentic engineering laboratory governed by the principle: **"Before you add power, add more control."**

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) installed and running locally (`http://127.0.0.1:11434`)
- Supported local models (e.g. `llama3.2:1b`, `sts-fast`)

---

## Quickstart

```bash
# Clone the repository
git clone https://github.com/loomlogic3/sts-ai-lab.git
cd sts-ai-lab

# Set up virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## CLI Commands

The STS AI Engine CLI installs the `sts` and `sts-ai-lab` command shortcuts when the package is installed with `pip install -e ".[dev]"`.

You can also run the same commands with `python3 -m app.cli` if the package is not installed.

### Interactive Sessions
- **Start STS Mentor**:
  ```bash
  sts mentor
  ```
- **Chat with a Specific Agent** (`sts_mentor`, `code_agent`, `research_agent`):
  ```bash
  sts chat code_agent
  ```

### Laboratory Inspection & Configuration
- **Lab Status & Connectivity**:
  ```bash
  sts status
  ```
- **List Available Agents**:
  ```bash
  sts agents
  ```
- **List Local Models**:
  ```bash
  sts models
  ```
- **List In-Session Tools**:
  ```bash
  sts tools
  ```
- **Project Structure Summary**:
  ```bash
  sts project
  ```

### Memory & Knowledge Base
- **View Saved Memory**:
  ```bash
  sts memory [agent_name]
  ```
- **Clear Persistent Memory**:
  ```bash
  sts clear [agent_name]
  ```
- **Search Knowledge Base**:
  ```bash
  sts knowledge "local AI stack"
  ```

### Experiment Logging
- **Log an Experiment Note**:
  ```bash
  sts experiment
  ```
- **List Logged Experiments**:
  ```bash
  sts experiments
  ```

---

## In-Session Commands & Tools

When chatting with STS Mentor or Code Agent, the following governed tools are available:

### Session & Knowledge
- `/memory` — Show saved conversation facts.
- `/clear` — Clear current agent memory.
- `/knowledge <query>` — Search the curated markdown knowledge base.
- `/log <note>` — Save a timestamped experiment note.
- `/experiments` — List existing experiment logs.
- `/tools` — Display all available in-session tools.
- `/bye` — Exit the interactive session.

### Safe Project Inspection (Read-Only)
- `/tree` — Show safe project directory hierarchy.
- `/read <file_path>` — Read a project file safely (blocks secrets and path traversal).
- `/search <keyword>` — Search across safe project files.
- `/grep <keyword>` — Search files and display matching line numbers.
- `/todos` — Search for `TODO` and `FIXME` items across the codebase.

### Python Code Intelligence (AST-Powered)
- `/index` — Build an in-memory index of project symbols.
- `/where <symbol>` — Find where a function, class, or import appears.
- `/explain <file_path>` — Provide a structural AST breakdown of a Python file.
- `/analyze <file.py>` — Generate a comprehensive code analysis report.
- `/functions <file.py>` — List defined functions in a Python file.
- `/classes <file.py>` — List defined classes in a Python file.
- `/imports <file.py>` — List imported modules in a Python file.
- `/project-map` — Display a fast architectural component map.

### Controlled Change Planning (Read-Only)
- `/risk <goal>` — Assess change risk before planning.
- `/plan-change <goal>` — Create a read-only plan identifying affected files.
- `/proposal <goal>` — Generate a change proposal combining risk and approach.
- `/propose-patch <goal>` — Draft a structured patch proposal.
- `/draft-patch <goal>` — Generate a human-readable patch plan without modifying files.
- `/design <goal>` — Create a read-only engineering design artifact.
- `/approval-required <goal>` — Check if a requested change requires explicit human approval.

---

## Architecture & Principles

- **Research first. Build second. Deploy third.**
- **Control before capability**: AI assists in observing, understanding, and planning; human engineers approve all actions.
- **Zero third-party runtime dependencies**: Built entirely with the Python standard library.
- **Defensive persistence**: Memory, approvals, and mutations use atomic filesystem writes with corruption recovery.

See further documentation in:
- [`docs/AI_LAB_CHARTER.md`](docs/AI_LAB_CHARTER.md) — Laboratory mission and core areas.
- [`docs/CODE_AGENT_ROADMAP.md`](docs/CODE_AGENT_ROADMAP.md) — Staged safety roadmap for coding agents.
- [`knowledge/ai_governance.md`](knowledge/ai_governance.md) — License-aware AI governance and model policies.
