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
