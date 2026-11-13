from pathlib import Path

import pytest

from srv1_core.paths import DataPaths, PathTraversalError, resolve_data_dir, safe_join


def test_env_override_wins(tmp_path: Path) -> None:
    env = {"SRV1_DATA_DIR": str(tmp_path / "x"), "PROGRAMDATA": r"C:\ProgramData"}
    assert resolve_data_dir(env) == (tmp_path / "x").resolve()


def test_default_is_programdata() -> None:
    assert resolve_data_dir({"PROGRAMDATA": r"C:\ProgramData"}) == Path(r"C:\ProgramData\SRV_1")


def test_ensure_creates_layout(tmp_path: Path) -> None:
    data = DataPaths(tmp_path / "d")
    data.ensure()
    data.ensure()
    assert data.logs_dir.is_dir()
    assert data.projects_dir.is_dir()
    assert data.plugins_dir.is_dir()
    assert data.config_file.parent == data.root


def test_safe_join_inside(tmp_path: Path) -> None:
    assert safe_join(tmp_path, "a", "b.txt") == tmp_path.resolve() / "a" / "b.txt"
    assert safe_join(tmp_path, "a/../b.txt") == tmp_path.resolve() / "b.txt"


@pytest.mark.parametrize(
    "parts",
    [
        ("..",),
        ("..", "x"),
        ("a", "..", "..", "x"),
        ("..\\..\\Windows",),
        ("\\Windows\\System32",),
        ("/etc/passwd",),
        ("C:\\Windows",),
        ("C:foo",),
        ("a.txt:stream",),
        ("",),
        ("a\x00b",),
        ("NUL",),
        ("sub/nul.txt",),
        ("com1",),
        ("a.txt.",),
        ("a.txt ",),
    ],
)
def test_safe_join_rejects_escape(tmp_path: Path, parts: tuple[str, ...]) -> None:
    with pytest.raises(PathTraversalError):
        safe_join(tmp_path, *parts)
