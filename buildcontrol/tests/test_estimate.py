"""Estimate calculations, workflow locking and versioning."""

from __future__ import annotations

import pytest

from app.models.enums import EstimateStatus, RoleCode, Unit
from app.services import estimate_service, expense_service, project_service
from app.services.estimate_service import EstimateLocked
from app.services.permissions import PermissionDenied
from tests.conftest import make_user


def _project(actor) -> int:
    return project_service.save_project(
        {"name": "Test loyiha", "planned_budget": 100_000_000, "status": "active"}, actor
    )


def _version(project_id: int) -> int:
    return estimate_service.list_versions(project_id)[0]["id"]


def test_plan_total_and_variance(admin) -> None:
    project_id = _project(admin)
    version_id = _version(project_id)
    section_id = estimate_service.add_section(version_id, "Beton ishlari", admin)
    estimate_service.save_item(
        {
            "section_id": section_id,
            "name": "Beton quyish",
            "unit": Unit.CBM.value,
            "quantity": 10,
            "plan_unit_price": 500_000,
        },
        admin,
    )
    tree = estimate_service.load_tree(project_id)
    item = tree.all_items()[0]
    assert item.plan_total == 5_000_000
    assert item.actual_total == 0
    assert item.variance == -5_000_000
    assert tree.plan_total == 5_000_000


def test_actual_cost_follows_approved_expenses(admin) -> None:
    project_id = _project(admin)
    version_id = _version(project_id)
    section_id = estimate_service.add_section(version_id, "Elektr", admin)
    item_id = estimate_service.save_item(
        {
            "section_id": section_id,
            "name": "Kabel tortish",
            "unit": Unit.METER.value,
            "quantity": 100,
            "plan_unit_price": 20_000,
        },
        admin,
    )
    expense_id = expense_service.save_expense(
        {
            "project_id": project_id,
            "estimate_item_id": item_id,
            "category": "material",
            "amount": 2_500_000,
        },
        admin,
    )
    # Pending expenses must not affect the actual cost.
    assert estimate_service.load_tree(project_id).all_items()[0].actual_total == 0

    expense_service.set_status(expense_id, "approved", admin)
    item = estimate_service.load_tree(project_id).all_items()[0]
    assert item.actual_total == 2_500_000
    assert item.variance == 500_000
    assert item.variance_percent == pytest.approx(25.0)


def test_approved_estimate_is_locked(admin) -> None:
    project_id = _project(admin)
    version_id = _version(project_id)
    section_id = estimate_service.add_section(version_id, "Pardoz", admin)
    estimate_service.set_status(version_id, EstimateStatus.APPROVED.value, admin)
    with pytest.raises(EstimateLocked):
        estimate_service.add_section(version_id, "Yangi bo'lim", admin)
    with pytest.raises(EstimateLocked):
        estimate_service.save_item(
            {"section_id": section_id, "name": "X", "quantity": 1, "plan_unit_price": 1}, admin
        )


def test_new_version_clones_tree_and_resets_actuals(admin) -> None:
    project_id = _project(admin)
    version_id = _version(project_id)
    section_id = estimate_service.add_section(version_id, "Beton", admin)
    estimate_service.save_item(
        {"section_id": section_id, "name": "Armatura", "quantity": 2, "plan_unit_price": 1_000_000},
        admin,
    )
    estimate_service.set_status(version_id, EstimateStatus.APPROVED.value, admin)
    new_id = estimate_service.create_new_version(project_id, admin, "narx o'zgardi")

    versions = estimate_service.list_versions(project_id)
    assert len(versions) == 2
    current = next(v for v in versions if v["is_current"])
    assert current["id"] == new_id
    assert current["status"] == EstimateStatus.DRAFT.value
    tree = estimate_service.load_tree(project_id, new_id)
    assert [i.name for i in tree.all_items()] == ["Armatura"]
    assert tree.plan_total == 2_000_000


def test_version_comparison_reports_changes(admin) -> None:
    project_id = _project(admin)
    version_id = _version(project_id)
    section_id = estimate_service.add_section(version_id, "Beton", admin)
    item_id = estimate_service.save_item(
        {"section_id": section_id, "name": "Armatura", "quantity": 2, "plan_unit_price": 1_000_000},
        admin,
    )
    new_id = estimate_service.create_new_version(project_id, admin)
    new_item = estimate_service.load_tree(project_id, new_id).all_items()[0]
    estimate_service.save_item({"plan_unit_price": 1_500_000}, admin, new_item.id)

    diff = estimate_service.compare_versions(version_id, new_id)
    changed = [row for row in diff if row["change"] == "changed"]
    assert changed and changed[0]["delta"] == 1_000_000
    del item_id


def test_estimator_cannot_approve(db) -> None:
    del db
    admin = make_user(RoleCode.ADMIN.value, "adm2")
    estimator = make_user(RoleCode.ESTIMATOR.value, "smetachi2")
    project_id = _project(admin)
    version_id = _version(project_id)
    estimate_service.set_status(version_id, EstimateStatus.SUBMITTED.value, estimator)
    with pytest.raises(PermissionDenied):
        estimate_service.set_status(version_id, EstimateStatus.APPROVED.value, estimator)
