"""Biznes jadvallari — katalog, mijozlar, buyurtmalar, ombor, moliya.

Bu jadvallar `event_log` dan proyeksiya qilinadi. Ya'ni ular kesh: agar
buzilsa, jurnaldan qayta qurish mumkin. Shuning uchun ular ustida
to'g'ridan-to'g'ri UPDATE qilish TAQIQLANADI — faqat proyektor yozadi.

Pul: `Numeric(18, 2)` emas, **butun son tiyin/so'm** ishlatiladi. Sabab —
SQLite'da REAL ustundagi SUM() aniqlikni yo'qotadi va moliyaviy hisobotda
tiyin farqi paydo bo'ladi. Miqdor (`quantity`) esa `Numeric(18, 3)`.
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from distribos.persistence.base import Base
from distribos.persistence.models.sync import utcnow

# --- sanoq turlari --------------------------------------------------------


class OrderState(enum.StrEnum):
    """Buyurtma holati (topshiriq §13). O'tishlar `domain/order.py` da qulflangan."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    APPROVED = "APPROVED"
    ALLOCATED = "ALLOCATED"
    PICKED = "PICKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"


class MovementType(enum.StrEnum):
    """Ombor harakati. Qoldiq SHU harakatlardan hisoblanadi, overwrite emas."""

    RECEIPT = "RECEIPT"
    SALE = "SALE"
    RETURN_IN = "RETURN_IN"
    RETURN_OUT = "RETURN_OUT"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    WRITE_OFF = "WRITE_OFF"
    ADJUSTMENT = "ADJUSTMENT"
    RESERVATION = "RESERVATION"
    RELEASE = "RELEASE"


#: Qaysi harakatlar qoldiqni oshiradi (+1) yoki kamaytiradi (-1).
#: `RESERVATION`/`RELEASE` erkin qoldiqqa ta'sir qiladi, jami qoldiqqa emas.
MOVEMENT_SIGN: dict[str, int] = {
    MovementType.RECEIPT: +1,
    MovementType.RETURN_IN: +1,
    MovementType.TRANSFER_IN: +1,
    MovementType.SALE: -1,
    MovementType.RETURN_OUT: -1,
    MovementType.TRANSFER_OUT: -1,
    MovementType.WRITE_OFF: -1,
    MovementType.ADJUSTMENT: +1,   # ishorasi miqdorning o'zida
    MovementType.RESERVATION: 0,
    MovementType.RELEASE: 0,
}


class PaymentDirection(enum.StrEnum):
    IN = "IN"      # kassa kirimi / mijoz to'lovi
    OUT = "OUT"    # kassa chiqimi


class CustomerKind(enum.StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"


# --- tashkilot ------------------------------------------------------------


class Organization(Base):
    __tablename__ = "org_organization"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    tax_id: Mapped[str | None] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class Branch(Base):
    __tablename__ = "org_branch"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("org_organization.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Warehouse(Base):
    __tablename__ = "org_warehouse"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_branch.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CashRegister(Base):
    __tablename__ = "org_cash_register"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_branch.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SalesTerritory(Base):
    __tablename__ = "org_territory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class User(Base):
    __tablename__ = "org_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))

    #: Argon2id/scrypt hash. Ochiq parol HECH QACHON saqlanmaydi.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="agent")
    territory_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_territory.id", ondelete="SET NULL")
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


# --- katalog --------------------------------------------------------------


class ProductCategory(Base):
    __tablename__ = "catalog_category"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("catalog_category.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Product(Base):
    __tablename__ = "catalog_product"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    barcode: Mapped[str | None] = mapped_column(String(60))

    name: Mapped[str] = mapped_column(String(250), nullable=False)
    category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("catalog_category.id", ondelete="SET NULL")
    )
    brand: Mapped[str | None] = mapped_column(String(120))

    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="dona")
    pack_size: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False, default=1)

    #: Pul — butun son (tiyin). REAL emas: SUM() aniqligi buzilmasin.
    purchase_price: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    retail_price: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    wholesale_price: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    agent_price: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    min_stock: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_path: Mapped[str | None] = mapped_column(String(400))

    #: Maydon darajasidagi versiya — konflikt hal qilish uchun (§13).
    field_versions: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        Index("ix_product_name", "name"),
        Index("ix_product_barcode", "barcode"),
        Index("ix_product_active", "is_active"),
    )


class ProductBatch(Base):
    """Partiya va yaroqlilik muddati."""

    __tablename__ = "catalog_batch"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalog_product.id", ondelete="CASCADE"), nullable=False
    )
    batch_code: Mapped[str] = mapped_column(String(60), nullable=False)
    expires_on: Mapped[dt.date | None] = mapped_column(Date)

    __table_args__ = (
        UniqueConstraint("product_id", "batch_code", name="uq_batch_product_code"),
        Index("ix_batch_expiry", "expires_on"),
    )


# --- mijozlar -------------------------------------------------------------


class Customer(Base):
    __tablename__ = "crm_customer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)

    kind: Mapped[str] = mapped_column(String(15), nullable=False, default=CustomerKind.COMPANY)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))

    territory_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_territory.id", ondelete="SET NULL")
    )
    assigned_agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_user.id", ondelete="SET NULL")
    )

    price_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="wholesale")
    credit_limit: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    payment_term_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    field_versions: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        Index("ix_customer_name", "name"),
        Index("ix_customer_agent", "assigned_agent_id"),
        Index("ix_customer_territory", "territory_id"),
    )


# --- buyurtmalar ----------------------------------------------------------


class Order(Base):
    __tablename__ = "sales_order"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)

    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("crm_customer.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_warehouse.id", ondelete="SET NULL")
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_user.id", ondelete="SET NULL")
    )

    state: Mapped[str] = mapped_column(String(20), nullable=False, default=OrderState.DRAFT)

    ordered_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_due: Mapped[dt.date | None] = mapped_column(Date)

    #: Hammasi tiyinda.
    subtotal: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    paid_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")

    note: Mapped[str | None] = mapped_column(Text)
    #: Qaysi qurilmada yaratilgan — konflikt tekshiruvida kerak.
    origin_device_id: Mapped[bytes | None] = mapped_column(LargeBinary(16))

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    lines: Mapped[list[OrderLine]] = relationship(
        "OrderLine", back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_order_customer", "customer_id"),
        Index("ix_order_state_date", "state", "ordered_at"),
        Index("ix_order_agent", "agent_id"),
        # Ro'yxat DOIM sana bo'yicha teskari tartiblanadi. Kompozit
        # (state, ordered_at) indeksi bunda ishlamaydi — `state`
        # qat'iy bo'lmaganda SQLite vaqtinchalik B-tree quradi.
        Index("ix_order_date", "ordered_at"),
    )


class OrderLine(Base):
    __tablename__ = "sales_order_line"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_order.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalog_product.id", ondelete="RESTRICT"), nullable=False
    )

    quantity: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False)
    #: Narx buyurtma vaqtida MUZLATILADI. Keyin katalog narxi o'zgarsa ham
    #: bu qator o'zgarmaydi — aks holda tarix qayta yoziladi.
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    line_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    returned_quantity: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False, default=0)

    order: Mapped[Order] = relationship("Order", back_populates="lines")

    __table_args__ = (Index("ix_order_line_product", "product_id"),)


# --- ombor ----------------------------------------------------------------


class InventoryMovement(Base):
    """Append-only ombor harakati.

    Qoldiq HECH QACHON to'g'ridan-to'g'ri yozilmaydi — u shu jadvaldan
    hisoblanadi (topshiriq §13). Shuning uchun bu jadvalda UPDATE/DELETE
    yo'q, faqat INSERT.
    """

    __tablename__ = "inv_movement"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("org_warehouse.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("catalog_product.id", ondelete="RESTRICT"), nullable=False
    )
    batch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("catalog_batch.id", ondelete="SET NULL")
    )

    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Ishorali miqdor: ADJUSTMENT manfiy bo'lishi mumkin.
    quantity: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False)
    unit_cost: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    #: Sabab hujjati (buyurtma, transfer, inventarizatsiya).
    reference_type: Mapped[str | None] = mapped_column(String(40))
    reference_id: Mapped[str | None] = mapped_column(String(36))

    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Hodisa jurnalidagi manba — audit zanjiri uzilmasin.
    source_event_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_movement_stock", "warehouse_id", "product_id", "occurred_at"),
        Index("ix_movement_reference", "reference_type", "reference_id"),
    )


class StockSnapshot(Base):
    """Qoldiq keshi — tezlik uchun.

    Bu HAQIQAT MANBAI EMAS. `inv_movement` dan hisoblanadi va istalgan
    vaqtda qayta qurilishi mumkin (`rebuild_stock`).
    """

    __tablename__ = "inv_stock_snapshot"

    warehouse_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    quantity: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False, default=0)
    reserved: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False, default=0)
    #: Qaysi harakatgacha hisoblangan — inkremental yangilash uchun.
    computed_through: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    @property
    def available(self) -> float:
        return float(self.quantity) - float(self.reserved)


# --- moliya ---------------------------------------------------------------


class Payment(Base):
    """To'lov. O'CHIRILMAYDI va tahrirlanmaydi — faqat reversal (§13)."""

    __tablename__ = "fin_payment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)

    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("crm_customer.id", ondelete="RESTRICT")
    )
    cash_register_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("org_cash_register.id", ondelete="SET NULL")
    )

    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    exchange_rate: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=1)

    method: Mapped[str] = mapped_column(String(20), nullable=False, default="cash")
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Bekor qiluvchi yozuv (reversal). To'lov o'chirilmaydi.
    reverses_payment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("fin_payment.id", ondelete="RESTRICT")
    )
    is_reversed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_event_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_payment_customer", "customer_id", "occurred_at"),
        Index("ix_payment_register", "cash_register_id", "occurred_at"),
    )


class PaymentAllocation(Base):
    """To'lovni buyurtmalarga taqsimlash."""

    __tablename__ = "fin_payment_allocation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fin_payment.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_order.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("payment_id", "order_id", name="uq_allocation_payment_order"),
    )


# --- agent va tashriflar --------------------------------------------------


class VisitRoute(Base):
    __tablename__ = "field_route"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("org_user.id", ondelete="CASCADE"), nullable=False
    )
    route_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    name: Mapped[str | None] = mapped_column(String(150))

    __table_args__ = (Index("ix_route_agent_date", "agent_id", "route_date"),)


class Visit(Base):
    __tablename__ = "field_visit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    route_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("field_route.id", ondelete="SET NULL")
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("crm_customer.id", ondelete="RESTRICT"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("org_user.id", ondelete="RESTRICT"), nullable=False
    )

    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(30))

    #: Lokatsiya faqat ruxsat berilgan bo'lsa yoziladi (§14.7).
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    photo_path: Mapped[str | None] = mapped_column(String(400))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_visit_agent_date", "agent_id", "started_at"),)


# --- audit ----------------------------------------------------------------


class AuditLog(Base):
    """Append-only audit jurnali.

    Oddiy foydalanuvchi o'chira olmasligi kerak — buni SQLite trigger
    ta'minlaydi (`persistence/triggers.py`), ORM darajasidagi qoida emas.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    actor_id: Mapped[str | None] = mapped_column(String(36))
    device_id: Mapped[bytes | None] = mapped_column(LargeBinary(16))

    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(64))

    #: Qisqa, maxfiy ma'lumotsiz tavsif. Payload BU YERGA YOZILMAYDI.
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(36))

    __table_args__ = (
        Index("ix_audit_time", "occurred_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_action", "action"),
    )
