from app.file_tools import read_file


def test_read_file_allows_project_file():
    content = read_file("README.md")
    assert "# sts-ai-lab" in content


def test_read_file_blocks_parent_traversal():
    content = read_file("../sts-ai-lab/README.md")
    assert content == "Blocked: this path is not allowed."


def test_read_file_blocks_absolute_path():
    content = read_file("/etc/passwd")
    assert content == "Blocked: this path is not allowed."
