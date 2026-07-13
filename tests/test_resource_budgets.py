import json

from app import file_tools, knowledge_search, ollama_client, prompt_builder
from app.config import OLLAMA_NUM_CONTEXT


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"response": "ok"}).encode("utf-8")


def test_read_file_truncates_large_file(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    note = project / "note.md"
    note.write_text("abcdef", encoding="utf-8")

    monkeypatch.setattr(file_tools, "PROJECT_ROOT", project)
    monkeypatch.setattr(file_tools, "MAX_FILE_READ_CHARS", 3)

    content = file_tools.read_file("note.md")

    assert content.startswith("abc")
    assert "resource budget reached" in content


def test_search_files_limits_results(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()

    for index in range(3):
        (project / f"match_{index}.txt").write_text("needle", encoding="utf-8")

    monkeypatch.setattr(file_tools, "PROJECT_ROOT", project)
    monkeypatch.setattr(file_tools, "MAX_SEARCH_RESULTS", 2)
    monkeypatch.setattr(file_tools, "MAX_SEARCH_FILES", 10)

    result = file_tools.search_files("needle")

    assert result.count("match_") == 2
    assert "resource budget reached" in result


def test_grep_files_limits_results(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "notes.txt").write_text("needle\nneedle\nneedle\n", encoding="utf-8")

    monkeypatch.setattr(file_tools, "PROJECT_ROOT", project)
    monkeypatch.setattr(file_tools, "MAX_SEARCH_RESULTS", 2)

    result = file_tools.grep_files("needle")

    assert result.count("notes.txt") == 2
    assert "resource budget reached" in result


def test_knowledge_search_limits_documents_and_text(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    for index in range(3):
        (knowledge_dir / f"doc_{index}.md").write_text(
            "topic " + ("x" * 20),
            encoding="utf-8",
        )

    monkeypatch.setattr(knowledge_search, "KNOWLEDGE_DIR", knowledge_dir)
    monkeypatch.setattr(knowledge_search, "MAX_KNOWLEDGE_DOCUMENTS", 2)
    monkeypatch.setattr(knowledge_search, "MAX_KNOWLEDGE_CHARS_PER_DOCUMENT", 8)

    result = knowledge_search.search_knowledge("topic")

    assert result.count("Source:") == 2
    assert "topic xx" in result
    assert "xxx" not in result
    assert "resource budget reached" in result


def test_prompt_builder_limits_final_prompt(monkeypatch):
    monkeypatch.setattr(prompt_builder, "MAX_PROMPT_CHARS", 20)

    prompt = prompt_builder.build_prompt(
        system_prompt="system",
        conversation="conversation",
        user_question="question",
        knowledge="knowledge",
    )

    assert len(prompt) > 20
    assert prompt.startswith("system")
    assert "resource budget reached" in prompt


def test_ollama_uses_configured_context(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", fake_urlopen)

    result = ollama_client.run_ollama("sts-fast", "hello")

    assert result == "ok"
    assert captured["payload"]["options"]["num_ctx"] == OLLAMA_NUM_CONTEXT
