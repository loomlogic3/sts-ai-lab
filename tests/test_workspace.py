import inspect
import os
from pathlib import Path

import pytest

from app import file_tools
from app.code_understanding import analyze_python_file
from app.project_index import build_project_index
from app.tool_router import route_tool
from app.workspace import DEFAULT_WORKSPACE, Workspace


class FakeMemory:
    def context(self):
        return ""


@pytest.fixture
def external_workspace(tmp_path):
    root = tmp_path / "project-x"
    root.mkdir()
    (root / "README.md").write_text(
        "External workspace marker\nsearch needle\n",
        encoding="utf-8",
    )
    (root / "module.py").write_text(
        "import json\n\n"
        "class Example:\n"
        "    pass\n\n"
        "def build_value():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    (root / "notes.txt").write_text(
        "TODO: external task\nneedle appears here\n",
        encoding="utf-8",
    )
    return Workspace(root)


def test_valid_external_workspace_is_canonical_and_stable(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    workspace = Workspace(root / ".")

    assert workspace.root == root.resolve()
    assert workspace.root.is_absolute()
    assert workspace.identity.startswith("workspace_")
    assert workspace.identity == Workspace(root).identity
    assert str(root) not in workspace.identity


def test_default_workspace_preserves_sts_ai_lab_behavior():
    assert DEFAULT_WORKSPACE.root == Path(__file__).resolve().parent.parent
    assert "# sts-ai-lab" in file_tools.read_file("README.md")


def test_nonexistent_workspace_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        Workspace(tmp_path / "missing")


def test_file_cannot_be_a_workspace(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        Workspace(file_path)


@pytest.mark.parametrize("path", ["../outside.txt", "../../outside.txt"])
def test_workspace_rejects_path_traversal(external_workspace, path):
    assert external_workspace.resolve_path(path) is None
    assert file_tools.read_file(path, external_workspace).startswith("Blocked:")


def test_workspace_rejects_absolute_target_path(external_workspace):
    assert external_workspace.resolve_path("/etc/passwd") is None
    assert file_tools.read_file(
        "/etc/passwd",
        external_workspace,
    ).startswith("Blocked:")


def test_symlink_escape_is_blocked_and_hidden(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("outside secret", encoding="utf-8")
    link = root / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable")

    workspace = Workspace(root)

    assert workspace.resolve_path("escape.txt") is None
    assert file_tools.read_file("escape.txt", workspace).startswith("Blocked:")
    assert "escape.txt" not in file_tools.project_tree(workspace=workspace)
    assert "outside secret" not in file_tools.search_files("secret", workspace)


def test_contained_symlink_is_allowed(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    target = root / "target.txt"
    target.write_text("contained", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")

    assert file_tools.read_file("link.txt", Workspace(root)) == "contained"


def test_tree_read_search_grep_and_todos_use_external_workspace(
    external_workspace,
):
    tree = file_tools.project_tree(workspace=external_workspace)

    assert "README.md" in tree
    assert "module.py" in tree
    assert "External workspace marker" in file_tools.read_file(
        "README.md",
        external_workspace,
    )
    assert "README.md" in file_tools.search_files(
        "External workspace marker",
        external_workspace,
    )
    assert "notes.txt:2:" in file_tools.grep_files(
        "needle appears",
        external_workspace,
    )
    assert "notes.txt:1:" in file_tools.find_todos(external_workspace)


def test_external_file_read_remains_bounded(external_workspace, monkeypatch):
    monkeypatch.setattr(file_tools, "MAX_FILE_READ_CHARS", 8)

    result = file_tools.read_file("README.md", external_workspace)

    assert result.startswith("External")
    assert "resource budget reached" in result


def test_python_inspection_uses_external_workspace(external_workspace):
    result = analyze_python_file("module.py", external_workspace)

    assert "- json" in result
    assert "- Example" in result
    assert "- build_value" in result


def test_project_index_uses_workspace_not_current_directory(
    external_workspace,
    tmp_path,
    monkeypatch,
):
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "wrong.py").write_text(
        "def wrong(): pass\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(unrelated)

    index = build_project_index(external_workspace)

    assert [item["file"] for item in index] == ["module.py"]
    assert index[0]["functions"] == ["build_value"]


def test_two_workspaces_do_not_leak_visibility(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "first.txt").write_text("first-only", encoding="utf-8")
    (second_root / "second.txt").write_text("second-only", encoding="utf-8")
    first = Workspace(first_root)
    second = Workspace(second_root)

    assert "first.txt" in file_tools.search_files("first-only", first)
    assert "second.txt" not in file_tools.project_tree(workspace=first)
    assert "first.txt" not in file_tools.project_tree(workspace=second)
    assert file_tools.read_file("second.txt", first) == "File not found: second.txt"


@pytest.mark.parametrize(
    "protected_path",
    [
        ".env",
        ".git/config",
        "data/private.json",
        "__pycache__/module.pyc",
    ],
)
def test_protected_workspace_paths_remain_blocked(
    tmp_path,
    protected_path,
):
    root = tmp_path / "project"
    target = root / protected_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("private", encoding="utf-8")
    workspace = Workspace(root)

    assert workspace.resolve_path(protected_path) is None
    assert file_tools.read_file(
        protected_path,
        workspace,
    ).startswith("Blocked:")
    assert protected_path.split("/")[0] not in file_tools.project_tree(
        workspace=workspace,
    )


def test_tool_router_dispatches_against_explicit_workspace(
    external_workspace,
):
    result = route_tool(
        "/read README.md",
        FakeMemory(),
        workspace=external_workspace,
    )

    assert "External workspace marker" in result


def test_workspace_operations_do_not_call_chdir(
    external_workspace,
    monkeypatch,
):
    def fail_chdir(path):
        raise AssertionError("workspace operations must not call chdir")

    monkeypatch.setattr(os, "chdir", fail_chdir)

    assert file_tools.project_tree(workspace=external_workspace)
    assert build_project_index(external_workspace)


def test_workspace_is_product_neutral():
    source = inspect.getsource(Workspace).lower()

    for product_name in (
        "civicos",
        "alerthub",
        "synthpos",
        "synthquant",
    ):
        assert product_name not in source


def test_engineering_file_access_has_one_canonical_root_owner():
    violations = []

    for path in sorted(Path("app").glob("*.py")):
        if path.name == "workspace.py":
            continue

        source = path.read_text(encoding="utf-8")
        forbidden_patterns = (
            "PROJECT_ROOT",
            'Path(".").rglob',
            "Path('.').rglob",
            "Path.cwd",
            "os.getcwd",
            "os.chdir",
        )
        for pattern in forbidden_patterns:
            if pattern in source:
                violations.append(f"{path}:{pattern}")

    assert violations == []
