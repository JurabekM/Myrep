"""Company profile, dictionaries, backup / restore and data export."""

from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.config import BACKUP_DIR, DB_PATH, REPORTS_DIR
from app.database.session import reset_engine, session_scope
from app.models.entities import (
    Counterparty,
    Expense,
    Material,
    Project,
    PurchaseRequest,
    User,
    WarehouseTransaction,
)
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require

#: Dictionary kinds editable from the settings page.
REF_KINDS: tuple[str, ...] = (
    "estimate_category",
    "unit",
    "project_status",
    "expense_category",
)


def get_company() -> dict:
    """Return the company profile."""
    with session_scope() as session:
        row = Repositories(session).company.get_or_create()
        return row.as_dict()


def save_company(data: dict, actor: CurrentUser) -> None:
    """Update the company profile."""
    require(actor.role_code, Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        repos = Repositories(session)
        row = repos.company.get_or_create()
        repos.company.update(row, **data)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.UPDATE,
            entity_type="CompanySettings",
            entity_id=row.id,
            description=row.name,
        )


def list_refs(kind: str) -> list[dict]:
    """Return dictionary entries of a kind."""
    with session_scope() as session:
        return [
            {
                "id": r.id,
                "kind": r.kind,
                "code": r.code,
                "name_uz": r.name_uz,
                "name_en": r.name_en,
                "order_index": r.order_index,
                "is_system": r.is_system,
                "is_archived": r.is_archived,
            }
            for r in Repositories(session).refs.of_kind(kind)
        ]


def save_ref(data: dict, actor: CurrentUser, ref_id: int | None = None) -> int:
    """Create or update a dictionary entry."""
    require(actor.role_code, Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        repos = Repositories(session)
        if ref_id:
            ref = repos.refs.get_or_raise(ref_id)
            repos.refs.update(ref, **data)
        else:
            ref = repos.refs.create(**data)
        return ref.id


def delete_ref(ref_id: int, actor: CurrentUser) -> None:
    """Archive a dictionary entry (system entries are protected)."""
    require(actor.role_code, Perm.SETTINGS_MANAGE)
    with session_scope() as session:
        repos = Repositories(session)
        ref = repos.refs.get_or_raise(ref_id)
        if ref.is_system:
            raise PermissionError("system dictionary entry")
        repos.refs.archive(ref, True)


# --------------------------------------------------------------------------- #
# Backup / restore
# --------------------------------------------------------------------------- #


def create_backup(actor: CurrentUser) -> Path:
    """Copy the SQLite database into the backup folder. Returns the new path."""
    require(actor.role_code, Perm.SETTINGS_MANAGE)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"buildcontrol_{stamp}.db"
    with session_scope() as session:
        session.execute(select(1))  # flush WAL through a checkpoint-friendly read
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.BACKUP,
            entity_type="Database",
            description=str(target),
        )
    shutil.copy2(DB_PATH, target)
    for suffix in ("-wal", "-shm"):
        extra = Path(str(DB_PATH) + suffix)
        if extra.exists():
            shutil.copy2(extra, Path(str(target) + suffix))
    return target


def list_backups() -> list[dict]:
    """Return the available backup files, newest first."""
    rows = []
    for path in sorted(BACKUP_DIR.glob("buildcontrol_*.db"), reverse=True):
        stat = path.stat()
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime),
            }
        )
    return rows


def restore_backup(path: str | Path, actor: CurrentUser) -> None:
    """Replace the live database with ``path``.

    The engine is disposed first; the caller is expected to restart the app.
    """
    require(actor.role_code, Perm.SETTINGS_MANAGE)
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(str(source))
    reset_engine()
    for suffix in ("-wal", "-shm"):
        extra = Path(str(DB_PATH) + suffix)
        if extra.exists():
            extra.unlink()
    shutil.copy2(source, DB_PATH)


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #

_EXPORTS = {
    "projects": (Project, ["id", "code", "name", "client", "address", "status", "planned_budget"]),
    "materials": (
        Material,
        ["id", "sku", "name", "category", "unit", "min_stock", "standard_price"],
    ),
    "counterparties": (Counterparty, ["id", "kind", "name", "tin", "phone", "email", "rating"]),
    "expenses": (Expense, ["id", "project_id", "category", "amount", "pay_date", "status"]),
    "purchases": (PurchaseRequest, ["id", "number", "project_id", "title", "quantity", "status"]),
    "stock": (
        WarehouseTransaction,
        ["id", "tx_date", "kind", "material_id", "quantity", "unit_price", "project_id"],
    ),
}


def export_tables(actor: CurrentUser, target_dir: str | Path | None = None) -> list[Path]:
    """Export the main tables to CSV files. Returns the written paths."""
    require(actor.role_code, Perm.SETTINGS_MANAGE)
    folder = Path(target_dir or REPORTS_DIR) / f"export_{datetime.now():%Y%m%d_%H%M%S}"
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with session_scope() as session:
        for name, (model, columns) in _EXPORTS.items():
            path = folder / f"{name}.csv"
            with path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(columns)
                for row in session.scalars(select(model)).all():
                    writer.writerow([getattr(row, column, "") for column in columns])
            written.append(path)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.BACKUP,
            entity_type="Export",
            description=str(folder),
        )
    return written


def seed_reference_data() -> None:
    """Populate the dictionaries with the built-in system entries."""
    from app.models.enums import ExpenseCategory, ProjectStatus, Unit
    from app.utils.i18n import CATALOG

    presets: list[tuple[str, list[tuple[str, str]]]] = [
        ("unit", [(m.value, f"enum.unit.{m.value}") for m in Unit]),
        (
            "project_status",
            [(m.value, f"enum.project_status.{m.value}") for m in ProjectStatus],
        ),
        (
            "expense_category",
            [(m.value, f"enum.exp_cat.{m.value}") for m in ExpenseCategory],
        ),
        (
            "estimate_category",
            [
                ("prep", ""),
                ("concrete", ""),
                ("masonry", ""),
                ("electrical", ""),
                ("plumbing", ""),
                ("finishing", ""),
                ("facade", ""),
                ("other", ""),
            ],
        ),
    ]
    defaults = {
        "prep": ("Tayyorlov ishlari", "Preparation"),
        "concrete": ("Beton ishlari", "Concrete works"),
        "masonry": ("G'isht ishlari", "Masonry"),
        "electrical": ("Elektr ishlari", "Electrical"),
        "plumbing": ("Santexnika", "Plumbing"),
        "finishing": ("Pardozlash", "Finishing"),
        "facade": ("Fasad", "Facade"),
        "other": ("Boshqa", "Other"),
    }
    with session_scope() as session:
        repos = Repositories(session)
        for kind, entries in presets:
            existing = {r.code for r in repos.refs.of_kind(kind)}
            for index, (code, key) in enumerate(entries):
                if code in existing:
                    continue
                if key and key in CATALOG:
                    uz, en = CATALOG[key]["uz"], CATALOG[key]["en"]
                else:
                    uz, en = defaults.get(code, (code, code))
                repos.refs.create(
                    kind=kind,
                    code=code,
                    name_uz=uz,
                    name_en=en,
                    order_index=index,
                    is_system=True,
                )


def ref_choices(kind: str, language: str = "uz") -> list[tuple[str, str]]:
    """Return ``[(code, label)]`` pairs from a dictionary."""
    rows = list_refs(kind)
    return [(r["code"], r["name_uz"] if language == "uz" else r["name_en"]) for r in rows]
