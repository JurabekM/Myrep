"""Test fixtures: an isolated in-file SQLite database per test session."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import session as db_session  # noqa: E402
from app.database.migrations import run_migrations  # noqa: E402
from app.models.enums import RoleCode  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.auth_service import CurrentUser  # noqa: E402


@pytest.fixture()
def db(tmp_path) -> Path:
    """Point the engine at a fresh database file and run migrations."""
    db_session.reset_engine()
    path = tmp_path / "test.db"
    db_session.init_engine(f"sqlite:///{path}")
    run_migrations()
    with db_session.session_scope() as session:
        auth_service.ensure_roles(session)
    yield path
    db_session.reset_engine()


def make_user(role_code: str = RoleCode.ADMIN.value, username: str = "tester") -> CurrentUser:
    """Create and return a user snapshot with the requested role."""
    return auth_service.create_user(
        username=username,
        password="secret123",
        full_name=f"Test {role_code}",
        role_code=role_code,
    )


@pytest.fixture()
def admin(db) -> CurrentUser:
    """An administrator account."""
    del db
    return make_user(RoleCode.ADMIN.value, "admin_test")


@pytest.fixture()
def manager(db) -> CurrentUser:
    """A project manager account."""
    del db
    return make_user(RoleCode.MANAGER.value, "manager_test")
