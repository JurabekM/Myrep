"""Human readable labels for enum codes plus combo-box option builders."""

from __future__ import annotations

from app.models.enums import (
    CounterpartyKind,
    EstimateItemStatus,
    EstimateStatus,
    ExpenseCategory,
    ExpenseStatus,
    OrderStatus,
    PaymentMethod,
    ProjectStatus,
    ProjectType,
    PurchaseStatus,
    RoleCode,
    StageStatus,
    TxKind,
    Unit,
)
from app.utils.i18n import tr

#: enum class -> i18n key prefix
_PREFIX: dict[type, str] = {
    RoleCode: "enum.role",
    ProjectType: "enum.project_type",
    ProjectStatus: "enum.project_status",
    EstimateStatus: "enum.estimate_status",
    EstimateItemStatus: "enum.item_status",
    Unit: "enum.unit",
    PurchaseStatus: "enum.purchase_status",
    OrderStatus: "enum.order_status",
    TxKind: "enum.tx",
    StageStatus: "enum.stage_status",
    CounterpartyKind: "enum.cp_kind",
    ExpenseStatus: "enum.expense_status",
    PaymentMethod: "enum.method",
    ExpenseCategory: "enum.exp_cat",
}


def label_of(enum_cls: type, code: str | None) -> str:
    """Return the localized label of ``code`` inside ``enum_cls``."""
    if not code:
        return "—"
    return tr(f"{_PREFIX[enum_cls]}.{code}")


def options(enum_cls: type, include_all: bool = False) -> list[tuple[str, str]]:
    """Return ``[(code, label), ...]`` suitable for a combo box."""
    items = [(m.value, label_of(enum_cls, m.value)) for m in enum_cls]
    if include_all:
        items.insert(0, ("", tr("all")))
    return items


# Convenience wrappers used across the UI ----------------------------------- #
def role_label(code: str | None) -> str:
    return label_of(RoleCode, code)


def project_type_label(code: str | None) -> str:
    return label_of(ProjectType, code)


def project_status_label(code: str | None) -> str:
    return label_of(ProjectStatus, code)


def estimate_status_label(code: str | None) -> str:
    return label_of(EstimateStatus, code)


def item_status_label(code: str | None) -> str:
    return label_of(EstimateItemStatus, code)


def unit_label(code: str | None) -> str:
    return label_of(Unit, code)


def purchase_status_label(code: str | None) -> str:
    return label_of(PurchaseStatus, code)


def order_status_label(code: str | None) -> str:
    return label_of(OrderStatus, code)


def tx_kind_label(code: str | None) -> str:
    return label_of(TxKind, code)


def stage_status_label(code: str | None) -> str:
    return label_of(StageStatus, code)


def cp_kind_label(code: str | None) -> str:
    return label_of(CounterpartyKind, code)


def expense_status_label(code: str | None) -> str:
    return label_of(ExpenseStatus, code)


def method_label(code: str | None) -> str:
    return label_of(PaymentMethod, code)


def expense_category_label(code: str | None) -> str:
    return label_of(ExpenseCategory, code)


def audit_action_label(code: str | None) -> str:
    """Localized label for an audit action code."""
    return tr(f"audit.{code}") if code else "—"
