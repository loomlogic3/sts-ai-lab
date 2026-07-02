# Code Agent Roadmap

The STS AI Lab may eventually explore Codex-like coding capabilities, but only through a safe staged roadmap.

## Principle

Control before capability.

## Roadmap

1. Read project files safely.
2. Explain code.
3. Suggest code changes.
4. Plan file edits without applying them.
5. Apply patches only with confirmation.
6. Run tests.
7. Review results.
8. Assist with Git commits only after human approval.

## Current Position

This is a future direction, not the immediate next build target.

The Code Agent should remain safe, auditable, and human-supervised.

---

## Current Safe Inspection Tools

The Code Agent now has read-only project inspection tools.

Available tools:

- `/tree` — Show safe project structure.
- `/read <file_path>` — Read a project file safely.
- `/search <keyword>` — Find files containing a keyword.
- `/grep <keyword>` — Find matching lines with line numbers.

## Safety Notes

These tools are read-only.

They do not edit files, run code, delete files, expose `.env`, or access blocked paths.

This keeps the Code Agent aligned with the roadmap:

Inspect first. Understand second. Modify later with human approval.

---

## Current Code Intelligence Tools

The Code Agent now has fast, read-only Python code understanding tools.

Available tools:

- `/index` — Build a Python project index.
- `/where <symbol>` — Find where a function, class, or import appears.
- `/imports <file.py>` — List imports in a Python file.
- `/classes <file.py>` — List classes in a Python file.
- `/functions <file.py>` — List functions in a Python file.
- `/explain <file.py>` — Explain a Python file using fast structural analysis.
- `/analyze <file.py>` — Combine imports, classes, functions, and explanation into one report.

## Current Stage

The Code Agent is still in the safe inspection and understanding stage.

It can inspect and explain code, but it cannot edit, delete, execute, or commit code.

Next stages remain:

1. Change planning.
2. Patch proposal.
3. Human-approved patch application.
4. Test running.
5. Git assistance after approval.
