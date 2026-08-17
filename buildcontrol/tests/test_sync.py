"""End-to-end replication tests driving two independent installations.

Each "device" is a separate SQLite database; they exchange data through the
folder transport, which exercises exactly the same engine code path as the
Supabase backend (append-only log + cursor).
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest

from app.database import session as db_session
from app.database.migrations import run_migrations
from app.models.enums import RoleCode, TxKind, Unit
from app.services import (
    auth_service,
    estimate_service,
    expense_service,
    project_service,
    warehouse_service,
)
from app.sync import engine as sync_engine
from app.sync.tracker import install as install_tracker
from app.sync.transports import FolderTransport


class Device:
    """A single BuildControl installation backed by its own database."""

    def __init__(self, name: str, path, folder=None, transport_factory=None) -> None:
        self.name = name
        self.path = path
        self.folder = folder
        self._transport_factory = transport_factory or (lambda: FolderTransport(folder, "test"))
        with self.active():
            run_migrations()
            with db_session.session_scope() as session:
                auth_service.ensure_roles(session)
                sync_engine.get_state(session).device_name = name

    @contextmanager
    def active(self):
        """Point the process-wide engine at this device's database."""
        db_session.reset_engine()
        db_session.init_engine(f"sqlite:///{self.path}")
        try:
            yield self
        finally:
            db_session.reset_engine()

    def sync(self) -> sync_engine.SyncReport:
        """Run one push + pull round."""
        with self.active():
            return sync_engine.synchronize(self._transport_factory())


@pytest.fixture()
def devices(tmp_path):
    """Two installations sharing one folder-based change log."""
    install_tracker()
    folder = tmp_path / "shared"
    folder.mkdir()
    first = Device("A", tmp_path / "a.db", folder)
    second = Device("B", tmp_path / "b.db", folder)
    yield first, second
    db_session.reset_engine()


def _admin(username: str = "admin"):
    return auth_service.create_user(
        username=username, password="secret123", full_name="Admin", role_code=RoleCode.ADMIN.value
    )


# --------------------------------------------------------------------------- #
# Basic replication
# --------------------------------------------------------------------------- #


def test_project_and_estimate_replicate(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_id = project_service.save_project(
            {"name": "Sinxron loyiha", "planned_budget": 50_000_000, "status": "active"}, actor
        )
        version_id = estimate_service.list_versions(project_id)[0]["id"]
        section_id = estimate_service.add_section(version_id, "Beton", actor)
        estimate_service.save_item(
            {
                "section_id": section_id,
                "name": "Beton quyish",
                "unit": Unit.CBM.value,
                "quantity": 10,
                "plan_unit_price": 500_000,
            },
            actor,
        )
    assert a.sync().ok

    report = b.sync()
    assert report.ok, report.errors
    assert report.applied > 0

    with b.active():
        projects = project_service.list_projects()
        assert [p.name for p in projects] == ["Sinxron loyiha"]
        tree = estimate_service.load_tree(projects[0].id)
        assert tree.plan_total == 5_000_000
        item = tree.all_items()[0]
        assert item.name == "Beton quyish"
        # The foreign key was rebuilt from the uid, not copied blindly.
        assert item.section_id == tree.roots[0].id


def test_uids_match_across_devices(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_service.save_project({"name": "Uid testi", "planned_budget": 1}, actor)
        with db_session.session_scope() as session:
            from app.models.entities import Project

            uid_a = session.query(Project).one().uid
    a.sync()
    b.sync()
    with b.active(), db_session.session_scope() as session:
        from app.models.entities import Project

        assert session.query(Project).one().uid == uid_a


def test_update_flows_back(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_id = project_service.save_project(
            {"name": "Reja", "planned_budget": 10_000_000}, actor
        )
    a.sync()
    b.sync()

    with b.active():
        actor_b = auth_service.authenticate("admin", "secret123")
        remote = project_service.list_projects()[0]
        project_service.save_project(
            {"name": "Reja (tuzatilgan)", "planned_budget": 12_000_000}, actor_b, remote.id
        )
    b.sync()
    a.sync()

    with a.active():
        row = project_service.get_project(project_id)
        assert row["name"] == "Reja (tuzatilgan)"
        assert row["planned_budget"] == 12_000_000


def test_delete_propagates(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_id = project_service.save_project({"name": "O'chirish", "planned_budget": 1}, actor)
        version_id = estimate_service.list_versions(project_id)[0]["id"]
        section_id = estimate_service.add_section(version_id, "Bo'lim", actor)
        item_id = estimate_service.save_item(
            {"section_id": section_id, "name": "Band", "quantity": 1, "plan_unit_price": 100}, actor
        )
    a.sync()
    b.sync()
    with b.active():
        assert (
            len(estimate_service.load_tree(project_service.list_projects()[0].id).all_items()) == 1
        )

    with a.active():
        actor = auth_service.authenticate("admin", "secret123")
        estimate_service.delete_item(item_id, actor)
    a.sync()
    b.sync()

    with b.active():
        tree = estimate_service.load_tree(project_service.list_projects()[0].id)
        assert tree.all_items() == []


# --------------------------------------------------------------------------- #
# Conflicts and merging
# --------------------------------------------------------------------------- #


def test_last_write_wins(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_id = project_service.save_project(
            {"name": "Konflikt", "planned_budget": 100}, actor
        )
    a.sync()
    b.sync()

    # Both edit the same row while offline; B writes last.
    with a.active():
        actor_a = auth_service.authenticate("admin", "secret123")
        project_service.save_project(
            {"name": "A varianti", "planned_budget": 111}, actor_a, project_id
        )
    with b.active():
        actor_b = auth_service.authenticate("admin", "secret123")
        remote_id = project_service.list_projects()[0].id
        project_service.save_project(
            {"name": "B varianti", "planned_budget": 222}, actor_b, remote_id
        )

    a.sync()
    b.sync()
    a.sync()

    with a.active():
        assert project_service.get_project(project_id)["name"] == "B varianti"
    with b.active():
        assert project_service.list_projects()[0].name == "B varianti"


def test_older_change_does_not_overwrite_newer(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_id = project_service.save_project({"name": "Eski", "planned_budget": 1}, actor)
    a.sync()
    b.sync()

    # A edits first, B edits afterwards, but A pushes last.
    with a.active():
        actor_a = auth_service.authenticate("admin", "secret123")
        project_service.save_project({"name": "Eskiroq", "planned_budget": 2}, actor_a, project_id)
    with b.active():
        actor_b = auth_service.authenticate("admin", "secret123")
        rid = project_service.list_projects()[0].id
        project_service.save_project({"name": "Yangiroq", "planned_budget": 3}, actor_b, rid)
    b.sync()
    a.sync()  # pushes the older edit and pulls the newer one
    b.sync()

    with b.active():
        assert project_service.list_projects()[0].name == "Yangiroq"


def test_same_natural_key_merges_instead_of_duplicating(devices) -> None:
    """Both machines seeded an `admin` account — they must merge into one row."""
    a, b = devices
    with a.active():
        _admin("admin")
    with b.active():
        _admin("admin")
    a.sync()
    b.sync()
    a.sync()

    for device in (a, b):
        with device.active(), db_session.session_scope() as session:
            from app.models.entities import User

            assert session.query(User).filter(User.username == "admin").count() == 1


# --------------------------------------------------------------------------- #
# Cross-module data
# --------------------------------------------------------------------------- #


def test_warehouse_and_expenses_replicate_with_costs(devices) -> None:
    a, b = devices
    with a.active():
        actor = _admin()
        project_id = project_service.save_project(
            {"name": "Ombor sync", "planned_budget": 100_000_000}, actor
        )
        version_id = estimate_service.list_versions(project_id)[0]["id"]
        section_id = estimate_service.add_section(version_id, "Beton", actor)
        item_id = estimate_service.save_item(
            {
                "section_id": section_id,
                "name": "Sement",
                "quantity": 100,
                "plan_unit_price": 50_000,
            },
            actor,
        )
        material_id = warehouse_service.save_material(
            {"sku": "S-1", "name": "Sement", "unit": Unit.PIECE.value, "standard_price": 55_000},
            actor,
        )
        warehouse_service.register_transaction(
            {
                "material_id": material_id,
                "kind": TxKind.IN.value,
                "quantity": 100,
                "unit_price": 55_000,
                "tx_date": date.today(),
            },
            actor,
        )
        warehouse_service.register_transaction(
            {
                "material_id": material_id,
                "kind": TxKind.OUT.value,
                "quantity": 40,
                "unit_price": 55_000,
                "project_id": project_id,
                "estimate_item_id": item_id,
                "tx_date": date.today(),
            },
            actor,
        )
        expense_id = expense_service.save_expense(
            {"project_id": project_id, "estimate_item_id": item_id, "amount": 1_000_000}, actor
        )
        expense_service.set_status(expense_id, "approved", actor)

    a.sync()
    report = b.sync()
    assert report.ok, report.errors

    with b.active():
        project = project_service.list_projects()[0]
        stock = next(r for r in warehouse_service.list_materials() if r.sku == "S-1")
        assert stock.balance == 60
        totals = project_service.get_totals(project.id)
        assert totals.material_issued == 2_200_000
        assert totals.committed == 1_000_000
        item = estimate_service.load_tree(project.id).all_items()[0]
        assert item.actual_total == 3_200_000


def test_device_does_not_reapply_its_own_changes(devices) -> None:
    a, _b = devices
    with a.active():
        actor = _admin()
        project_service.save_project({"name": "Echo", "planned_budget": 1}, actor)
    first = a.sync()
    assert first.pushed > 0
    assert first.applied == 0  # its own rows are recognised and skipped
    assert first.skipped_own == first.pulled

    second = a.sync()  # cursor already past them: nothing left to do
    assert (second.pushed, second.pulled, second.applied) == (0, 0, 0)
    with a.active():
        assert len(project_service.list_projects()) == 1


def test_pending_counter_and_status(devices) -> None:
    a, _b = devices
    with a.active():
        actor = _admin()
        assert sync_engine.pending_changes() > 0
        project_service.save_project({"name": "Holat", "planned_budget": 1}, actor)
        state = sync_engine.status()
        assert state["pending"] > 0
        assert state["device_id"]
    a.sync()
    with a.active():
        assert sync_engine.pending_changes() == 0
        assert sync_engine.status()["cursor"]


# --------------------------------------------------------------------------- #
# Upgrading an installation created before synchronisation existed
# --------------------------------------------------------------------------- #


def test_v1_database_upgrades_and_backfills_uids(tmp_path) -> None:
    """A database created by v1.0.0 gains uid/sync_ts without losing data."""
    from sqlalchemy import text

    install_tracker()
    path = tmp_path / "legacy.db"
    db_session.reset_engine()
    db_session.init_engine(f"sqlite:///{path}")
    run_migrations()
    with db_session.session_scope() as session:
        auth_service.ensure_roles(session)
    actor = _admin("legacy")
    project_id = project_service.save_project({"name": "Eski baza", "planned_budget": 500}, actor)

    # Rewind the schema to the pre-sync shape.
    engine = db_session.get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM schema_version WHERE version >= 2"))
        for table in ("projects", "users"):
            conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_uid"))
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN uid"))
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN sync_ts"))
    db_session.reset_engine()

    db_session.init_engine(f"sqlite:///{path}")
    assert run_migrations() >= 2

    with db_session.session_scope() as session:
        from app.models.entities import Project, User

        project = session.get(Project, project_id)
        assert project.name == "Eski baza"
        assert project.uid and project.sync_ts
        uids = [u.uid for u in session.query(User).all()]
        assert all(uids) and len(set(uids)) == len(uids)
    db_session.reset_engine()


def test_foreign_keys_survive_a_natural_key_merge(devices) -> None:
    """A row referencing a locally-merged parent must still resolve.

    Both devices seed their own `admin` user; they merge on the username but
    keep their own uid. Anything pointing at the other device's uid has to be
    translated through the alias table instead of being dropped.
    """
    a, b = devices
    with a.active():
        actor_a = _admin("admin")
    with b.active():
        _admin("admin")

    a.sync()
    b.sync()
    a.sync()

    with a.active():
        manager_id = auth_service.authenticate("admin", "secret123").id
        project_service.save_project(
            {"name": "Mas'ul bilan", "planned_budget": 1_000_000, "manager_id": manager_id},
            actor_a,
        )
    a.sync()

    report = b.sync()
    assert report.ok, report.errors
    with b.active():
        row = project_service.get_project(project_service.list_projects()[0].id)
        assert row["name"] == "Mas'ul bilan"
        # the manager reference was rebuilt against B's own admin row
        assert row["manager_id"] is not None
        assert row["manager_name"] == "Admin"
