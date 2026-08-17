"""SQLAlchemy ORM entities for BuildControl.

Money is stored as ``Float`` (SQLite REAL) in the project base currency (UZS)
and rounded at presentation time. A ``currency`` column is kept on money-bearing
documents so a second currency can be introduced without a schema break.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.config import BASE_CURRENCY
from app.database.base import ArchivableMixin, Base, PKMixin, SyncMixin, TimestampMixin
from app.models.enums import (
    CounterpartyKind,
    EstimateItemStatus,
    EstimateStatus,
    ExpenseStatus,
    OrderStatus,
    ProjectStatus,
    ProjectType,
    PurchaseStatus,
    StageStatus,
    TxKind,
    Unit,
)

# --------------------------------------------------------------------------- #
# Security
# --------------------------------------------------------------------------- #


class Role(Base, PKMixin, SyncMixin):
    """A named permission set (``admin``, ``manager`` ...)."""

    __tablename__ = "roles"

    code = Column(String(32), unique=True, nullable=False)
    name_uz = Column(String(64), nullable=False)
    name_en = Column(String(64), nullable=False)
    description = Column(Text, default="")

    users = relationship("User", back_populates="role")

    def display(self, lang: str = "uz") -> str:
        return self.name_uz if lang == "uz" else self.name_en


class User(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """Application user."""

    __tablename__ = "users"

    username = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(128), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    email = Column(String(128), default="")
    phone = Column(String(64), default="")
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)

    role = relationship("Role", back_populates="users")

    @property
    def role_code(self) -> str:
        return self.role.code if self.role else ""

    @property
    def label(self) -> str:
        return self.full_name or self.username


class RefItem(Base, PKMixin, SyncMixin, ArchivableMixin):
    """Generic user-editable dictionary (categories, units, statuses ...)."""

    __tablename__ = "ref_items"
    __table_args__ = (UniqueConstraint("kind", "code", name="uq_ref_kind_code"),)

    kind = Column(String(32), nullable=False, index=True)
    code = Column(String(48), nullable=False)
    name_uz = Column(String(96), nullable=False)
    name_en = Column(String(96), nullable=False)
    order_index = Column(Integer, default=0)
    is_system = Column(Boolean, default=False, nullable=False)


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #


class Project(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """A construction / renovation project."""

    __tablename__ = "projects"

    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(160), nullable=False)
    client = Column(String(160), default="")
    address = Column(String(255), default="")
    project_type = Column(String(32), default=ProjectType.RENOVATION.value)
    start_date = Column(Date)
    end_date = Column(Date)
    manager_id = Column(Integer, ForeignKey("users.id"))
    planned_budget = Column(Float, default=0.0, nullable=False)
    currency = Column(String(8), default=BASE_CURRENCY, nullable=False)
    status = Column(String(32), default=ProjectStatus.PLANNED.value, index=True)
    notes = Column(Text, default="")

    manager = relationship("User", foreign_keys=[manager_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    estimate_versions = relationship(
        "EstimateVersion", back_populates="project", cascade="all, delete-orphan"
    )
    stages = relationship("WorkStage", back_populates="project", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base, PKMixin, SyncMixin):
    """Link table: which users work on which project."""

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_member"),)

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_in_project = Column(String(64), default="")

    project = relationship("Project", back_populates="members")
    user = relationship("User")


# --------------------------------------------------------------------------- #
# Estimate
# --------------------------------------------------------------------------- #


class EstimateVersion(Base, PKMixin, SyncMixin, TimestampMixin):
    """One revision of a project estimate (bill of quantities)."""

    __tablename__ = "estimate_versions"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_no = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default=EstimateStatus.DRAFT.value, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    note = Column(Text, default="")
    created_by_id = Column(Integer, ForeignKey("users.id"))
    approved_by_id = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)

    project = relationship("Project", back_populates="estimate_versions")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    sections = relationship(
        "EstimateSection", back_populates="version", cascade="all, delete-orphan"
    )

    @property
    def label(self) -> str:
        return f"v{self.version_no}"


class EstimateSection(Base, PKMixin, SyncMixin):
    """A chapter / sub-chapter of the estimate tree."""

    __tablename__ = "estimate_sections"

    version_id = Column(
        Integer, ForeignKey("estimate_versions.id", ondelete="CASCADE"), nullable=False
    )
    parent_id = Column(Integer, ForeignKey("estimate_sections.id", ondelete="CASCADE"))
    code = Column(String(32), default="")
    name = Column(String(160), nullable=False)
    order_index = Column(Integer, default=0)

    version = relationship("EstimateVersion", back_populates="sections")
    parent = relationship(
        "EstimateSection",
        back_populates="children",
        remote_side="EstimateSection.id",
    )
    children = relationship(
        "EstimateSection",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    items = relationship("EstimateItem", back_populates="section", cascade="all, delete-orphan")


class EstimateItem(Base, PKMixin, SyncMixin):
    """A single priced line of the estimate."""

    __tablename__ = "estimate_items"

    section_id = Column(
        Integer, ForeignKey("estimate_sections.id", ondelete="CASCADE"), nullable=False
    )
    code = Column(String(32), default="")
    name = Column(String(200), nullable=False)
    category = Column(String(64), default="")
    unit = Column(String(16), default=Unit.PIECE.value)
    quantity = Column(Float, default=0.0, nullable=False)
    plan_unit_price = Column(Float, default=0.0, nullable=False)
    #: Cached aggregate of expenses + material issues booked against this line.
    actual_cost = Column(Float, default=0.0, nullable=False)
    progress_percent = Column(Float, default=0.0, nullable=False)
    responsible_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(32), default=EstimateItemStatus.PLANNED.value)
    note = Column(Text, default="")
    order_index = Column(Integer, default=0)

    section = relationship("EstimateSection", back_populates="items")
    responsible = relationship("User")

    # -- derived values ----------------------------------------------------- #
    @property
    def plan_total(self) -> float:
        """Planned total = quantity x planned unit price."""
        return round((self.quantity or 0.0) * (self.plan_unit_price or 0.0), 2)

    @property
    def actual_unit_price(self) -> float:
        """Actual unit price = actual total / quantity (0 when no quantity)."""
        return round((self.actual_cost or 0.0) / self.quantity, 2) if self.quantity else 0.0

    @property
    def variance(self) -> float:
        """Actual total - planned total (positive means overspend)."""
        return round((self.actual_cost or 0.0) - self.plan_total, 2)

    @property
    def variance_percent(self) -> float:
        """Variance expressed as a share of the planned total."""
        plan = self.plan_total
        return round(self.variance / plan * 100.0, 2) if plan else 0.0


# --------------------------------------------------------------------------- #
# Counterparties
# --------------------------------------------------------------------------- #


class Counterparty(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """Single-table base for suppliers and contractors."""

    __tablename__ = "counterparties"

    kind = Column(String(32), nullable=False, default=CounterpartyKind.SUPPLIER.value)
    name = Column(String(160), nullable=False)
    tin = Column(String(32), default="")
    phone = Column(String(64), default="")
    email = Column(String(128), default="")
    address = Column(String(255), default="")
    bank_details = Column(Text, default="")
    category = Column(String(96), default="")
    rating = Column(Float, default=0.0)
    note = Column(Text, default="")

    # contractor-specific
    contract_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    completed_work = Column(Float, default=0.0)
    delay_days = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    disputes = Column(Integer, default=0)

    __mapper_args__ = {"polymorphic_on": kind, "polymorphic_identity": "counterparty"}


class Supplier(Counterparty):
    """A material / service vendor."""

    __mapper_args__ = {"polymorphic_identity": CounterpartyKind.SUPPLIER.value}


class Contractor(Counterparty):
    """A works contractor."""

    __mapper_args__ = {"polymorphic_identity": CounterpartyKind.CONTRACTOR.value}


# --------------------------------------------------------------------------- #
# Purchasing
# --------------------------------------------------------------------------- #


class PurchaseRequest(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """A request to buy a material or service for a project."""

    __tablename__ = "purchase_requests"

    number = Column(String(32), default="")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    estimate_item_id = Column(Integer, ForeignKey("estimate_items.id", ondelete="SET NULL"))
    off_estimate = Column(Boolean, default=False, nullable=False)
    title = Column(String(200), nullable=False)
    unit = Column(String(16), default=Unit.PIECE.value)
    quantity = Column(Float, default=0.0, nullable=False)
    est_price = Column(Float, default=0.0, nullable=False)
    needed_date = Column(Date)
    delivery_address = Column(String(255), default="")
    responsible_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(32), default=PurchaseStatus.DRAFT.value, index=True)
    note = Column(Text, default="")

    project = relationship("Project")
    estimate_item = relationship("EstimateItem")
    responsible = relationship("User")
    quotes = relationship("SupplierQuote", back_populates="request", cascade="all, delete-orphan")
    orders = relationship("PurchaseOrder", back_populates="request", cascade="all, delete-orphan")

    @property
    def est_total(self) -> float:
        return round((self.quantity or 0.0) * (self.est_price or 0.0), 2)


class SupplierQuote(Base, PKMixin, SyncMixin, TimestampMixin):
    """A vendor offer answering a :class:`PurchaseRequest`."""

    __tablename__ = "supplier_quotes"

    request_id = Column(
        Integer, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id = Column(Integer, ForeignKey("counterparties.id"))
    supplier_name = Column(String(160), default="")
    contact = Column(String(128), default="")
    unit_price = Column(Float, default=0.0, nullable=False)
    delivery_cost = Column(Float, default=0.0, nullable=False)
    delivery_days = Column(Integer, default=0)
    payment_terms = Column(String(128), default="")
    file_path = Column(String(255), default="")
    is_selected = Column(Boolean, default=False, nullable=False)

    request = relationship("PurchaseRequest", back_populates="quotes")
    supplier = relationship("Counterparty")

    def total_value(self, quantity: float) -> float:
        """Total cost of ownership = goods price + delivery cost."""
        return round((self.unit_price or 0.0) * (quantity or 0.0) + (self.delivery_cost or 0.0), 2)


class PurchaseOrder(Base, PKMixin, SyncMixin, TimestampMixin):
    """Order issued to the winning supplier."""

    __tablename__ = "purchase_orders"

    order_no = Column(String(32), nullable=False)
    request_id = Column(
        Integer, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False
    )
    quote_id = Column(Integer, ForeignKey("supplier_quotes.id", ondelete="SET NULL"))
    supplier_id = Column(Integer, ForeignKey("counterparties.id"))
    order_date = Column(Date, default=date.today)
    total_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(32), default=OrderStatus.NEW.value)
    note = Column(Text, default="")

    request = relationship("PurchaseRequest", back_populates="orders")
    quote = relationship("SupplierQuote")
    supplier = relationship("Counterparty")


# --------------------------------------------------------------------------- #
# Warehouse
# --------------------------------------------------------------------------- #


class Material(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """Catalogue entry for a stocked material."""

    __tablename__ = "materials"

    sku = Column(String(48), unique=True, nullable=False)
    name = Column(String(160), nullable=False)
    category = Column(String(96), default="")
    unit = Column(String(16), default=Unit.PIECE.value)
    min_stock = Column(Float, default=0.0, nullable=False)
    standard_price = Column(Float, default=0.0, nullable=False)
    supplier_id = Column(Integer, ForeignKey("counterparties.id"))
    note = Column(Text, default="")

    supplier = relationship("Counterparty")
    transactions = relationship(
        "WarehouseTransaction", back_populates="material", cascade="all, delete-orphan"
    )


class WarehouseTransaction(Base, PKMixin, SyncMixin, TimestampMixin):
    """Stock movement (receipt, issue, return, adjustment, loss)."""

    __tablename__ = "warehouse_transactions"

    tx_date = Column(Date, default=date.today, nullable=False, index=True)
    kind = Column(String(16), nullable=False, default=TxKind.IN.value, index=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Float, default=0.0, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    estimate_item_id = Column(Integer, ForeignKey("estimate_items.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("users.id"))
    doc_path = Column(String(255), default="")
    note = Column(Text, default="")

    material = relationship("Material", back_populates="transactions")
    project = relationship("Project")
    estimate_item = relationship("EstimateItem")
    user = relationship("User")

    @property
    def signed_quantity(self) -> float:
        """Quantity with the sign it contributes to the stock balance."""
        if self.kind in (TxKind.IN.value, TxKind.RETURN.value, TxKind.ADJUST.value):
            return self.quantity or 0.0
        return -(self.quantity or 0.0)

    @property
    def total(self) -> float:
        return round((self.quantity or 0.0) * (self.unit_price or 0.0), 2)


# --------------------------------------------------------------------------- #
# Schedule
# --------------------------------------------------------------------------- #


class WorkStage(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """A scheduled work package rendered on the Gantt timeline."""

    __tablename__ = "work_stages"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(160), nullable=False)
    section_id = Column(Integer, ForeignKey("estimate_sections.id", ondelete="SET NULL"))
    plan_start = Column(Date)
    plan_end = Column(Date)
    actual_start = Column(Date)
    actual_end = Column(Date)
    progress_percent = Column(Float, default=0.0, nullable=False)
    responsible_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(32), default=StageStatus.NOT_STARTED.value, index=True)
    dependencies = Column(String(128), default="")  # comma separated stage ids
    note = Column(Text, default="")
    order_index = Column(Integer, default=0)

    project = relationship("Project", back_populates="stages")
    responsible = relationship("User")
    logs = relationship("DailySiteLog", back_populates="stage", cascade="all, delete-orphan")

    @property
    def dependency_ids(self) -> list[int]:
        return [int(x) for x in (self.dependencies or "").split(",") if x.strip().isdigit()]


class DailySiteLog(Base, PKMixin, SyncMixin, TimestampMixin):
    """Daily site diary entry."""

    __tablename__ = "daily_site_logs"

    log_date = Column(Date, default=date.today, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    stage_id = Column(Integer, ForeignKey("work_stages.id", ondelete="SET NULL"))
    work_done = Column(Text, default="")
    progress_percent = Column(Float, default=0.0)
    workers_count = Column(Integer, default=0)
    issue = Column(Text, default="")
    photo_path = Column(String(255), default="")
    author_id = Column(Integer, ForeignKey("users.id"))

    project = relationship("Project")
    stage = relationship("WorkStage", back_populates="logs")
    author = relationship("User")


# --------------------------------------------------------------------------- #
# Money
# --------------------------------------------------------------------------- #


class Expense(Base, PKMixin, SyncMixin, TimestampMixin, ArchivableMixin):
    """A cost booked against a project (and optionally an estimate line)."""

    __tablename__ = "expenses"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(32), default="material")
    estimate_item_id = Column(Integer, ForeignKey("estimate_items.id", ondelete="SET NULL"))
    counterparty_id = Column(Integer, ForeignKey("counterparties.id", ondelete="SET NULL"))
    amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(8), default=BASE_CURRENCY, nullable=False)
    pay_date = Column(Date, default=date.today, index=True)
    method = Column(String(16), default="transfer")
    invoice_no = Column(String(64), default="")
    doc_path = Column(String(255), default="")
    note = Column(Text, default="")
    status = Column(String(32), default=ExpenseStatus.PENDING.value, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    approved_by_id = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)

    project = relationship("Project", back_populates="expenses")
    estimate_item = relationship("EstimateItem")
    counterparty = relationship("Counterparty")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    payments = relationship("Payment", back_populates="expense", cascade="all, delete-orphan")


class Payment(Base, PKMixin, SyncMixin, TimestampMixin):
    """An actual money transfer settling (part of) an expense."""

    __tablename__ = "payments"

    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, default=0.0, nullable=False)
    pay_date = Column(Date, default=date.today, nullable=False)
    method = Column(String(16), default="transfer")
    note = Column(Text, default="")
    created_by_id = Column(Integer, ForeignKey("users.id"))

    expense = relationship("Expense", back_populates="payments")
    created_by = relationship("User")


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #


class Attachment(Base, PKMixin, SyncMixin, TimestampMixin):
    """File reference attached to any entity."""

    __tablename__ = "attachments"

    entity_type = Column(String(48), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    title = Column(String(160), default="")
    file_path = Column(String(400), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User")


class AuditLog(Base, PKMixin, SyncMixin):
    """Immutable trail of every meaningful change."""

    __tablename__ = "audit_logs"

    ts = Column(DateTime, default=datetime.now, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String(64), default="")
    action = Column(String(48), nullable=False, index=True)
    entity_type = Column(String(48), default="")
    entity_id = Column(Integer)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    description = Column(Text, default="")
    old_value = Column(Text, default="")
    new_value = Column(Text, default="")

    user = relationship("User")


class CompanySettings(Base, PKMixin, SyncMixin):
    """Single-row company profile used in report headers."""

    __tablename__ = "company_settings"

    name = Column(String(160), default="BuildControl")
    logo_path = Column(String(255), default="")
    address = Column(String(255), default="")
    phone = Column(String(64), default="")
    requisites = Column(Text, default="")
    currency = Column(String(8), default=BASE_CURRENCY)
    language = Column(String(8), default="uz")


__all__ = [
    "Attachment",
    "AuditLog",
    "CompanySettings",
    "Contractor",
    "Counterparty",
    "DailySiteLog",
    "EstimateItem",
    "EstimateSection",
    "EstimateVersion",
    "Expense",
    "Material",
    "Payment",
    "Project",
    "ProjectMember",
    "PurchaseOrder",
    "PurchaseRequest",
    "RefItem",
    "Role",
    "Supplier",
    "SupplierQuote",
    "User",
    "WarehouseTransaction",
    "WorkStage",
]
