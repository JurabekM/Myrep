import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class Tenant(AuditMixin, Base):
    """Do'kon egasining hisobi. Barcha biznes ma'lumotlar tenant_id bilan bog'lanadi."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))


class User(AuditMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))


class Store(AuditMixin, Base):
    """Filial / do'kon. RLS bilan tenant bo'yicha izolyatsiya qilinadi."""

    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))


ROLES = ("owner", "manager", "cashier", "warehouse", "viewer")


class Membership(AuditMixin, Base):
    """Foydalanuvchining tenant ichidagi roli. store_id NULL bo'lsa, barcha filiallarga tegishli."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "store_id", name="uq_membership"),
        CheckConstraint(
            "role IN ('owner', 'manager', 'cashier', 'warehouse', 'viewer')",
            name="ck_membership_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("stores.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20))


class RefreshToken(Base):
    """Refresh token'lar faqat hash ko'rinishida saqlanadi. family_id orqali rotatsiya zanjiri kuzatiladi."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Faza 2: katalog, yetkazuvchilar, kirim va qoldiq ledger'i
# ---------------------------------------------------------------------------

UNITS = ("dona", "kg", "litr", "metr", "quti", "paket")
MOVEMENT_KINDS = ("receipt", "sale", "sale_return", "adjustment", "writeoff")


class Category(AuditMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_category_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))


class Product(AuditMixin, Base):
    """Tovar. Narxlar so'mda butun son (tiyinsiz), miqdor esa o'nlik kasr bo'lishi mumkin (kg, litr)."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="ck_product_sale_price"),
        CheckConstraint("cost_price >= 0", name="ck_product_cost_price"),
        CheckConstraint("min_stock >= 0", name="ck_product_min_stock"),
        CheckConstraint(f"unit IN {UNITS}", name="ck_product_unit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(10), default="dona", server_default="dona")
    sale_price: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    cost_price: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ProductBarcode(AuditMixin, Base):
    __tablename__ = "product_barcodes"
    __table_args__ = (UniqueConstraint("tenant_id", "barcode", name="uq_barcode_per_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), index=True)
    barcode: Mapped[str] = mapped_column(String(64))


class Supplier(AuditMixin, Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Purchase(AuditMixin, Base):
    """Kirim hujjati (yetkazuvchidan qabul). Har bir qator uchun 'receipt' harakat yoziladi."""

    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("stores.id"), index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("suppliers.id"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    total_cost: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    purchase_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchases.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost: Mapped[int] = mapped_column(BigInteger)


class StockMovement(Base):
    """Qoldiq ledger'i. Faqat qo'shiladi: ilova roli UPDATE/DELETE huquqiga ega emas (0002 migratsiya).

    Qoldiq = SUM(qty). qty ishorasi: kirim +, chiqim -.
    """

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(f"kind IN {MOVEMENT_KINDS}", name="ck_movement_kind"),
        CheckConstraint("qty <> 0", name="ck_movement_qty_nonzero"),
        Index("ix_stock_movements_store_product", "store_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("stores.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"))
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    kind: Mapped[str] = mapped_column(String(20))
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
