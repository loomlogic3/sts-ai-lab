"""
Canonical workspace boundary for read-only engineering operations.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


PROTECTED_WORKSPACE_PARTS = frozenset({
    ".env",
    ".git",
    "__pycache__",
    "data",
})


@dataclass(frozen=True)
class Workspace:
    """
    One validated project root and its containment policy.
    """

    root: Path | str
    identity: str = field(init=False)

    def __post_init__(self) -> None:
        root = Path(self.root).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Workspace does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Workspace is not a directory: {root}")

        digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "identity", f"workspace_{digest}")

    def resolve_path(self, path_text: str | Path) -> Path | None:
        """
        Resolve an allowed relative path contained by this workspace.
        """

        raw_path = Path(path_text).expanduser()
        if raw_path.is_absolute() or ".." in raw_path.parts:
            return None
        if any(part in PROTECTED_WORKSPACE_PARTS for part in raw_path.parts):
            return None

        candidate = self.root / raw_path
        try:
            resolved = candidate.resolve()
            relative = resolved.relative_to(self.root)
        except (OSError, RuntimeError, ValueError):
            return None

        if any(part in PROTECTED_WORKSPACE_PARTS for part in relative.parts):
            return None
        return resolved

    def relative_path(self, path: Path) -> Path | None:
        """
        Return an allowed lexical relative path for a discovered workspace path.
        """

        try:
            lexical_relative = path.relative_to(self.root)
        except ValueError:
            return None

        if any(
            part in PROTECTED_WORKSPACE_PARTS
            for part in lexical_relative.parts
        ):
            return None
        if self.resolve_path(lexical_relative) is None:
            return None
        return lexical_relative


DEFAULT_WORKSPACE = Workspace(Path(__file__).resolve().parent.parent)


def get_workspace(workspace: Workspace | None = None) -> Workspace:
    """
    Return an explicit workspace or the backward-compatible default.
    """

    return workspace or DEFAULT_WORKSPACE
