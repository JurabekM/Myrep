"""Warehouse balance rules and their effect on estimate actuals."""

from __future__ import annotations

import pytest

from app.models.enums import RoleCode, TxKind, Unit
from app.services import estimate_service, project_service, warehouse_service
from app.services.permissions import PermissionDenied
from app.services.warehouse_service import StockError
from tests.conftest import make_user


def _material(actor) -> int:
    return warehouse_service.save_material(
        {
            "sku": "MAT-100",
            "name": "Sement M400",
            "unit": Unit.PIECE.value,
            "min_stock": 50,
            "standard_price": 55_000,
        },
        actor,
    )


def test_balance_adds_receipts_and_subtracts_issues(admin) -> None:
    material_id = _material(admin)
    warehouse_service.register_transaction(
        {
            "material_id": material_id,
            "kind": TxKind.IN.value,
            "quantity": 200,
            "unit_price": 55_000,
        },
        admin,
    )
    warehouse_service.register_transaction(
        {
            "material_id": material_id,
            "kind": TxKind.OUT.value,
            "quantity": 30,
            "unit_price": 55_000,
        },
        admin,
    )
    warehouse_service.register_transaction(
        {
            "material_id": material_id,
            "kind": TxKind.RETURN.value,
            "quantity": 5,
            "unit_price": 55_000,
        },
        admin,
    )
    row = next(r for r in warehouse_service.list_materials() if r.id == material_id)
    assert row.balance == 175
    assert row.is_low is False


def test_low_stock_flag(admin) -> None:
    material_id = _material(admin)
    warehouse_service.register_transaction(
        {"material_id": material_id, "kind": TxKind.IN.value, "quantity": 40, "unit_price": 55_000},
        admin,
    )
    row = next(r for r in warehouse_service.list_materials() if r.id == material_id)
    assert row.is_low is True
    assert [r.id for r in warehouse_service.low_stock()] == [material_id]


def test_issue_above_balance_is_rejected(admin) -> None:
    material_id = _material(admin)
    warehouse_service.register_transaction(
        {"material_id": material_id, "kind": TxKind.IN.value, "quantity": 10, "unit_price": 1000},
        admin,
    )
    with pytest.raises(StockError) as excinfo:
        warehouse_service.register_transaction(
            {
                "material_id": material_id,
                "kind": TxKind.OUT.value,
                "quantity": 11,
                "unit_price": 1000,
            },
            admin,
        )
    assert excinfo.value.key == "not_enough_stock"


def test_issue_updates_estimate_actual(admin) -> None:
    project_id = project_service.save_project(
        {"name": "Ombor loyihasi", "planned_budget": 50_000_000}, admin
    )
    version_id = estimate_service.list_versions(project_id)[0]["id"]
    section_id = estimate_service.add_section(version_id, "Beton", admin)
    item_id = estimate_service.save_item(
        {"section_id": section_id, "name": "Sement", "quantity": 100, "plan_unit_price": 50_000},
        admin,
    )
    material_id = _material(admin)
    warehouse_service.register_transaction(
        {
            "material_id": material_id,
            "kind": TxKind.IN.value,
            "quantity": 100,
            "unit_price": 55_000,
        },
        admin,
    )
    warehouse_service.register_transaction(
        {
            "material_id": material_id,
            "kind": TxKind.OUT.value,
            "quantity": 60,
            "unit_price": 55_000,
            "project_id": project_id,
            "estimate_item_id": item_id,
        },
        admin,
    )
    item = estimate_service.load_tree(project_id).all_items()[0]
    assert item.actual_total == 3_300_000
    totals = project_service.get_totals(project_id)
    assert totals.material_issued == 3_300_000
    assert totals.actual == 3_300_000


def test_viewer_cannot_move_stock(db) -> None:
    del db
    admin = make_user(RoleCode.ADMIN.value, "adm3")
    viewer = make_user(RoleCode.VIEWER.value, "kuzatuvchi3")
    material_id = _material(admin)
    with pytest.raises(PermissionDenied):
        warehouse_service.register_transaction(
            {
                "material_id": material_id,
                "kind": TxKind.IN.value,
                "quantity": 1,
                "unit_price": 100,
            },
            viewer,
        )
