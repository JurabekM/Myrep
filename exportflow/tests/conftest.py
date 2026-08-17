"""Shared pytest fixtures: an isolated database per test session."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# The application resolves its paths at import time, so the data directory must
# be redirected before anything from ``app`` is imported.
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="exportflow-tests-"))
os.environ["EXPORTFLOW_HOME"] = str(_TMP_ROOT)

from app.database.engine import reset_engine, session_scope  # noqa: E402
from app.database.migrations import run_migrations  # noqa: E402
from app.database.seed import seed_demo_data, seed_reference_data  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.auth_service import CurrentUser  # noqa: E402
from app.services.permissions import PERMISSIONS  # noqa: E402
from app.utils.enums import ROLE_ADMIN, ROLE_SALES_MANAGER  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    """Create a fresh database with reference and demo data."""
    reset_engine()
    run_migrations()
    with session_scope() as session:
        seed_reference_data(session)
        seed_demo_data(session)
    yield
    reset_engine()


@pytest.fixture()
def session() -> Iterator:
    """A transactional session for one test."""
    with session_scope() as scoped:
        yield scoped


@pytest.fixture()
def admin() -> CurrentUser:
    """Administrator snapshot with every permission."""
    return CurrentUser(
        id=1,
        username="admin",
        full_name="System Administrator",
        role_code=ROLE_ADMIN,
        role_name="Administrator",
        language="en",
        permissions=frozenset(PERMISSIONS),
    )


@pytest.fixture()
def sales_manager() -> CurrentUser:
    """Sales manager snapshot (cannot approve quotations)."""
    from app.services.permissions import permissions_for_role

    return CurrentUser(
        id=3,
        username="nigora",
        full_name="Nigora Yusupova",
        role_code=ROLE_SALES_MANAGER,
        role_name="Sales Manager",
        language="ru",
        permissions=frozenset(permissions_for_role(ROLE_SALES_MANAGER)),
    )


@pytest.fixture()
def viewer() -> CurrentUser:
    """Read-only user."""
    from app.services.permissions import permissions_for_role
    from app.utils.enums import ROLE_VIEWER

    return CurrentUser(
        id=6,
        username="viewer",
        full_name="Read Only",
        role_code=ROLE_VIEWER,
        role_name="Viewer",
        language="en",
        permissions=frozenset(permissions_for_role(ROLE_VIEWER)),
    )


@pytest.fixture()
def demo_password() -> str:
    """Password used by the demo accounts."""
    _ = hash_password, auth_service
    return "admin123"
