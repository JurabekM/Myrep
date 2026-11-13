"""0-bosqich: skelet butunligi va qat'iy cheklovlar qo'riqchisi."""

import importlib
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("srv1_core", "srv1_sdk", "srv1_shell")

# Loyiha promptidagi TAQIQLANGAN ro'yxat (PyPI nomlari, normallashtirilgan).
FORBIDDEN = frozenset(
    {
        "docker",
        "pandas",
        "pyqt6-webengine",
        "celery",
        "rq",
        "psycopg",
        "psycopg2",
        "psycopg2-binary",
        "asyncpg",
        "redis",
        "aiomqtt",
    }
)


def _pyproject() -> dict[str, Any]:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _requirement_name(requirement: str) -> str:
    name = re.split(r"[\s\[<>=!~;@]", requirement.strip(), maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_dependencies() -> set[str]:
    data = _pyproject()
    project: dict[str, Any] = data["project"]
    groups: list[list[str]] = [project.get("dependencies", [])]
    groups += project.get("optional-dependencies", {}).values()
    groups += data.get("dependency-groups", {}).values()
    return {_requirement_name(req) for group in groups for req in group}


@pytest.mark.parametrize("package", PACKAGES)
def test_package_imports_with_matching_version(package: str) -> None:
    module = importlib.import_module(package)
    assert module.__version__ == _pyproject()["project"]["version"]


def test_python_is_312() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_no_forbidden_dependencies() -> None:
    assert _declared_dependencies().isdisjoint(FORBIDDEN)


@pytest.mark.parametrize("directory", ["core", "sdk", "shell", "plugins", "tests", "docs", "tools"])
def test_layout_directory_exists(directory: str) -> None:
    assert (ROOT / directory).is_dir()


def test_requirement_name_normalisation() -> None:
    assert _requirement_name("PyQt6_WebEngine>=6.6") == "pyqt6-webengine"
    assert _requirement_name("psycopg[binary] ; sys_platform == 'win32'") == "psycopg"
