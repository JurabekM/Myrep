"""Role permissions, budget warnings, purchasing rules and contractor rating."""

from __future__ import annotations

import pytest

from app.models.enums import RoleCode
from app.services import counterparty_service, expense_service, project_service, purchase_service
from app.services.permissions import Perm, PermissionDenied, has_perm
from app.services.purchase_service import PurchaseRuleError
from app.utils.security import hash_password, validate_password, verify_password
from tests.conftest import make_user


# -- permissions -------------------------------------------------------------- #
def test_role_matrix() -> None:
    assert has_perm(RoleCode.ADMIN.value, Perm.SETTINGS_MANAGE)
    assert has_perm(RoleCode.MANAGER.value, Perm.EXPENSE_APPROVE)
    assert not has_perm(RoleCode.ESTIMATOR.value, Perm.EXPENSE_APPROVE)
    assert not has_perm(RoleCode.ESTIMATOR.value, Perm.ESTIMATE_APPROVE)
    assert has_perm(RoleCode.ESTIMATOR.value, Perm.ESTIMATE_EDIT)
    assert has_perm(RoleCode.STOREKEEPER.value, Perm.WAREHOUSE_EDIT)
    assert not has_perm(RoleCode.STOREKEEPER.value, Perm.ESTIMATE_EDIT)
    assert has_perm(RoleCode.VIEWER.value, Perm.REPORT_VIEW)
    assert not has_perm(RoleCode.VIEWER.value, Perm.PROJECT_EDIT)


def test_viewer_cannot_create_project(db) -> None:
    del db
    viewer = make_user(RoleCode.VIEWER.value, "viewer_p")
    with pytest.raises(PermissionDenied):
        project_service.save_project({"name": "X", "planned_budget": 1}, viewer)


# -- budget ------------------------------------------------------------------- #
def test_budget_warning_and_over_budget_flag(admin) -> None:
    project_id = project_service.save_project(
        {"name": "Budjet testi", "planned_budget": 10_000_000}, admin
    )
    expense_id = expense_service.save_expense(
        {"project_id": project_id, "category": "material", "amount": 6_000_000}, admin
    )
    expense_service.set_status(expense_id, "approved", admin)

    assert expense_service.would_exceed_budget(project_id, 3_000_000) is False
    assert expense_service.would_exceed_budget(project_id, 5_000_000) is True

    second = expense_service.save_expense(
        {"project_id": project_id, "category": "labor", "amount": 5_000_000}, admin
    )
    expense_service.set_status(second, "approved", admin)
    totals = project_service.get_totals(project_id)
    assert totals.actual == 11_000_000
    assert totals.remaining == -1_000_000
    assert totals.is_over_budget is True


def test_payment_closes_expense(admin) -> None:
    project_id = project_service.save_project(
        {"name": "To'lov", "planned_budget": 5_000_000}, admin
    )
    expense_id = expense_service.save_expense(
        {"project_id": project_id, "category": "material", "amount": 1_000_000}, admin
    )
    expense_service.add_payment(expense_id, {"amount": 400_000}, admin)
    row = expense_service.list_expenses(project_id=project_id)[0]
    assert row["paid"] == 400_000
    assert row["status"] == "pending"

    expense_service.add_payment(expense_id, {"amount": 600_000}, admin)
    row = expense_service.list_expenses(project_id=project_id)[0]
    assert row["status"] == "paid"
    assert row["balance"] == 0


# -- purchasing ---------------------------------------------------------------- #
def test_request_requires_estimate_item_unless_off_estimate(admin) -> None:
    project_id = project_service.save_project({"name": "Xarid", "planned_budget": 1_000_000}, admin)
    with pytest.raises(PurchaseRuleError):
        purchase_service.save_request(
            {"project_id": project_id, "title": "Sement", "quantity": 5}, admin
        )
    request_id = purchase_service.save_request(
        {"project_id": project_id, "title": "Sement", "quantity": 5, "off_estimate": True}, admin
    )
    assert request_id


def test_best_quote_balances_price_and_lead_time(admin) -> None:
    project_id = project_service.save_project({"name": "Taklif", "planned_budget": 1}, admin)
    request_id = purchase_service.save_request(
        {"project_id": project_id, "title": "Laminat", "quantity": 100, "off_estimate": True},
        admin,
    )
    purchase_service.save_quote(
        request_id,
        {"supplier_name": "Arzon", "unit_price": 100, "delivery_cost": 5_000, "delivery_days": 30},
        admin,
    )
    purchase_service.save_quote(
        request_id,
        {"supplier_name": "Tez", "unit_price": 105, "delivery_cost": 500, "delivery_days": 3},
        admin,
    )
    quotes = purchase_service.list_quotes(request_id)
    cheapest = next(q for q in quotes if q.is_cheapest)
    best = next(q for q in quotes if q.is_best)
    fastest = next(q for q in quotes if q.is_fastest)
    assert cheapest.supplier_name == "Tez"  # total value includes delivery
    assert fastest.supplier_name == "Tez"
    assert best.supplier_name == "Tez"


def test_order_requires_selected_quote(admin) -> None:
    project_id = project_service.save_project({"name": "Buyurtma", "planned_budget": 1}, admin)
    request_id = purchase_service.save_request(
        {"project_id": project_id, "title": "G'isht", "quantity": 10, "off_estimate": True}, admin
    )
    with pytest.raises(PurchaseRuleError):
        purchase_service.create_order(request_id, admin)
    quote_id = purchase_service.save_quote(
        request_id, {"supplier_name": "A", "unit_price": 1_000, "delivery_cost": 0}, admin
    )
    purchase_service.select_quote(quote_id, admin)
    order_id = purchase_service.create_order(request_id, admin)
    order = next(o for o in purchase_service.list_orders() if o["id"] == order_id)
    assert order["total_amount"] == 10_000
    assert order["status"] == "new"


# -- contractor rating ---------------------------------------------------------- #
def test_rating_formula() -> None:
    perfect = counterparty_service.compute_rating(
        delay_days=0, contract_amount=100, paid_amount=100, quality_score=5, disputes=0
    )
    assert perfect == 5.0
    poor = counterparty_service.compute_rating(
        delay_days=60, contract_amount=100, paid_amount=140, quality_score=2, disputes=4
    )
    assert poor < 2.5


# -- passwords ------------------------------------------------------------------ #
def test_password_hashing_roundtrip() -> None:
    hashed = hash_password("Parol123")
    assert hashed != "Parol123"
    assert verify_password("Parol123", hashed)
    assert not verify_password("boshqa", hashed)
    assert validate_password("123") == "password_too_short"
    assert validate_password("uzunparol") is None


def test_purchase_order_pdf(admin, tmp_path) -> None:
    from app.reports.pdf_reports import export_purchase_order

    project_id = project_service.save_project({"name": "PDF", "planned_budget": 1}, admin)
    request_id = purchase_service.save_request(
        {"project_id": project_id, "title": "Profil", "quantity": 20, "off_estimate": True}, admin
    )
    quote_id = purchase_service.save_quote(
        request_id,
        {
            "supplier_name": "Stroy",
            "unit_price": 30_000,
            "delivery_cost": 200_000,
            "delivery_days": 3,
        },
        admin,
    )
    purchase_service.select_quote(quote_id, admin)
    order_id = purchase_service.create_order(request_id, admin)
    path = export_purchase_order(order_id, tmp_path / "order.pdf")
    assert path.exists() and path.stat().st_size > 1000
