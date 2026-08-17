"""Domain enumerations.

Every enum member stores a stable machine code in the database; the human
readable label is resolved through the i18n catalogue with the key
``enum.<enum_name>.<code>``.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String enum whose value is the code persisted in the database."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)

    @classmethod
    def codes(cls) -> list[str]:
        return [m.value for m in cls]


class RoleCode(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    ESTIMATOR = "estimator"
    STOREKEEPER = "storekeeper"
    VIEWER = "viewer"


class ProjectType(StrEnum):
    NEW_BUILD = "new_build"
    RENOVATION = "renovation"
    INTERIOR = "interior"
    FACADE = "facade"
    OTHER = "other"


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EstimateStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REVISION = "revision"


class EstimateItemStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    NEEDS_PURCHASE = "needs_purchase"
    DONE = "done"
    CANCELLED = "cancelled"


class Unit(StrEnum):
    PIECE = "piece"
    KG = "kg"
    TON = "ton"
    METER = "m"
    SQM = "m2"
    CBM = "m3"
    HOUR = "hour"
    DAY = "day"
    SERVICE = "service"
    LITER = "liter"
    SET = "set"


class PurchaseStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ORDERED = "ordered"
    PARTIAL = "partial"
    COMPLETED = "completed"


class OrderStatus(StrEnum):
    NEW = "new"
    SENT = "sent"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TxKind(StrEnum):
    """Warehouse transaction kinds."""

    IN = "in"
    OUT = "out"
    RETURN = "return"
    ADJUST = "adjust"
    LOSS = "loss"


class StageStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DELAYED = "delayed"
    DONE = "done"
    BLOCKED = "blocked"


class CounterpartyKind(StrEnum):
    SUPPLIER = "supplier"
    CONTRACTOR = "contractor"


class ExpenseStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"


class ExpenseCategory(StrEnum):
    MATERIAL = "material"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    TRANSPORT = "transport"
    SUBCONTRACT = "subcontract"
    OVERHEAD = "overhead"
    OTHER = "other"


#: Statuses that count as money already committed to the project.
COMMITTED_EXPENSE_STATUSES = (ExpenseStatus.APPROVED.value, ExpenseStatus.PAID.value)
#: Statuses that count as money actually spent.
ACTUAL_EXPENSE_STATUSES = (ExpenseStatus.APPROVED.value, ExpenseStatus.PAID.value)
