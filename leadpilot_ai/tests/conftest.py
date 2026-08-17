"""Shared pytest fixtures: an isolated SQLite database per test session."""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The data directory must be set before app.config is imported.
_TMP_DIR = tempfile.mkdtemp(prefix="leadpilot_tests_")
os.environ["LEADPILOT_DATA_DIR"] = _TMP_DIR
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.database.engine import init_engine, reset_engine, session_scope  # noqa: E402
from app.database.migrations import run_migrations  # noqa: E402
from app.database.seed import seed_all  # noqa: E402
from app.models.enums import RoleName  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.auth_service import CurrentUser  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    """Create a fresh database with the demo dataset for the whole session."""
    db_path = Path(_TMP_DIR) / "test.db"
    engine = init_engine(f"sqlite:///{db_path.as_posix()}")
    run_migrations(engine)
    with session_scope() as session:
        auth_service.ensure_roles(session)
    seed_all()
    yield
    reset_engine()


@pytest.fixture()
def admin() -> CurrentUser:
    """Signed-in administrator."""
    return auth_service.authenticate("admin", "admin123")


@pytest.fixture()
def operator() -> CurrentUser:
    """Signed-in operator (Dilnoza)."""
    return auth_service.authenticate("dilnoza", "dilnoza123")


@pytest.fixture()
def second_operator() -> CurrentUser:
    """Signed-in second operator (Jamshid)."""
    return auth_service.authenticate("jamshid", "jamshid123")


@pytest.fixture()
def viewer() -> CurrentUser:
    """A read-only viewer created on demand."""
    try:
        return auth_service.authenticate("kuzatuvchi", "kuzatuvchi123")
    except auth_service.AuthError:
        auth_service.create_user(
            username="kuzatuvchi",
            password="kuzatuvchi123",
            full_name="Kuzatuvchi Test",
            role_name=RoleName.VIEWER,
        )
        return auth_service.authenticate("kuzatuvchi", "kuzatuvchi123")
