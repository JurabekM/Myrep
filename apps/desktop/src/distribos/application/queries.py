"""O'qish tomoni — UI uchun so'rovlar.

UI hech qachon ORM modelini to'g'ridan-to'g'ri ushlamaydi: sessiya yopilgach
lazy-load qilinadigan atribut `DetachedInstanceError` beradi. Shuning uchun
bu yerda hamma narsa oddiy dataclass'ga ko'chiriladi.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from distribos.persistence.models import (
    AuditLog,
    ConflictRecord,
    Customer,
    DeadLetter,
    DeliveryState,
    EventLog,
    InventoryMovement,
    Order,
    OrderLine,
    OutboxEntry,
    Payment,
    PeerDevice,
    Product,
    StockSnapshot,
    Visit,
    Warehouse,
)


@dataclass(frozen=True, slots=True)
class ProductRow:
    id: str
    sku: str
    name: str
    unit: str
    barcode: str | None
    wholesale_price: int
    retail_price: int
    agent_price: int
    min_stock: Decimal
    stock: Decimal
    is_active: bool

    @property
    def below_minimum(self) -> bool:
        return self.min_stock > 0 and self.stock < self.min_stock


@dataclass(frozen=True, slots=True)
class CustomerRow:
    id: str
    code: str
    name: str
    phone: str | None
    price_tier: str
    credit_limit: int
    debt: int
    order_count: int
    is_active: bool

    @property
    def over_limit(self) -> bool:
        return self.credit_limit > 0 and self.debt > self.credit_limit


@dataclass(frozen=True, slots=True)
class OrderRow:
    id: str
    number: str
    customer_name: str
    state: str
    ordered_at: dt.datetime
    total: int
    paid_total: int
    line_count: int
    delivery_state: str

    @property
    def outstanding(self) -> int:
        return self.total - self.paid_total


@dataclass(frozen=True, slots=True)
class StockRow:
    warehouse_name: str
    product_sku: str
    product_name: str
    quantity: Decimal
    reserved: Decimal
    min_stock: Decimal

    @property
    def available(self) -> Decimal:
        return self.quantity - self.reserved

    @property
    def below_minimum(self) -> bool:
        return self.min_stock > 0 and self.quantity < self.min_stock


@dataclass(frozen=True, slots=True)
class PaymentRow:
    id: str
    number: str
    direction: str
    customer_name: str
    amount: int
    method: str
    occurred_at: dt.datetime
    is_reversed: bool


@dataclass(frozen=True, slots=True)
class DeviceRow:
    device_id: bytes
    display_name: str
    platform: str
    role: str
    state: str
    last_seen_at: dt.datetime | None
    last_applied_sequence: int
    is_full_replica: bool


@dataclass(frozen=True, slots=True)
class ConflictRow:
    id: int
    aggregate_type: str
    aggregate_id: str
    field_name: str | None
    strategy: str
    status: str
    resolution: str | None
    local_value: str | None
    remote_value: str | None
    detected_at: dt.datetime


@dataclass(frozen=True, slots=True)
class SyncSummary:
    queued: int
    dead_letters: int
    open_conflicts: int
    total_events: int
    unapplied_events: int
    devices_active: int
    devices_revoked: int
    last_event_at: dt.datetime | None


# --- katalog --------------------------------------------------------------


def list_products(session: Session, *, search: str = "", limit: int = 500) -> list[ProductRow]:
    stock = (
        select(
            StockSnapshot.product_id,
            func.sum(StockSnapshot.quantity).label("total"),
        )
        .group_by(StockSnapshot.product_id)
        .subquery()
    )
    stmt = (
        select(Product, func.coalesce(stock.c.total, 0))
        .outerjoin(stock, stock.c.product_id == Product.id)
        .order_by(Product.name)
        .limit(limit)
    )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Product.name.ilike(pattern), Product.sku.ilike(pattern),
                Product.barcode.ilike(pattern))
        )

    return [
        ProductRow(
            id=product.id, sku=product.sku, name=product.name, unit=product.unit,
            barcode=product.barcode, wholesale_price=product.wholesale_price,
            retail_price=product.retail_price, agent_price=product.agent_price,
            min_stock=Decimal(str(product.min_stock)),
            stock=Decimal(str(quantity or 0)), is_active=product.is_active,
        )
        for product, quantity in session.execute(stmt).all()
    ]


def find_product_by_barcode(session: Session, barcode: str) -> ProductRow | None:
    """Shtrix-kod bo'yicha ANIQ moslik.

    Avval bu `list_products(search=...)` ni chaqirardi, ya'ni uchta
    ustunda `LIKE '%…%'` va qoldiq subquery'si bilan to'liq skan bo'lardi
    (100 000 mahsulotda 163 ms). Skaner har o'qishda chaqiriladi, shuning
    uchun bu yo'l indeksdan foydalanadigan aniq so'rovga almashtirildi.
    """
    product = session.execute(
        select(Product).where(Product.barcode == barcode, Product.is_active.is_(True))
    ).scalars().first()
    if product is None:
        return None

    quantity = session.execute(
        select(func.coalesce(func.sum(StockSnapshot.quantity), 0))
        .where(StockSnapshot.product_id == product.id)
    ).scalar_one()

    return ProductRow(
        id=product.id, sku=product.sku, name=product.name, unit=product.unit,
        barcode=product.barcode, wholesale_price=product.wholesale_price,
        retail_price=product.retail_price, agent_price=product.agent_price,
        min_stock=Decimal(str(product.min_stock)),
        stock=Decimal(str(quantity or 0)), is_active=product.is_active,
    )


# --- mijozlar -------------------------------------------------------------


#: Mijoz qarzi = buyurtmalar - sof to'lovlar.
#:
#: DIQQAT: `Order.paid_total` ISHLATILMAYDI. U faqat to'lov aniq
#: buyurtmaga taqsimlanganda (`PaymentAllocation`) o'sadi. Real savdoda
#: esa mijoz ko'pincha "hisobga" umumiy summa to'laydi va uni hech qaysi
#: buyurtmaga biriktirmaydi — o'shanda qarzi kamayishi SHART.
#:
#: Bekor qilingan to'lovni alohida chiqarib tashlash SHART EMAS: bekor
#: qilish teskari yozuv yaratadi (IN uchun OUT), ya'ni yig'indida
#: o'z-o'zidan nolga chiqadi.
def _net_payments_subquery():
    return (
        select(
            Payment.customer_id.label("customer_id"),
            func.sum(
                case((Payment.direction == "IN", Payment.amount), else_=-Payment.amount)
            ).label("net_paid"),
        )
        .where(Payment.customer_id.is_not(None))
        .group_by(Payment.customer_id)
        .subquery()
    )


def list_customers(session: Session, *, search: str = "", limit: int = 500) -> list[CustomerRow]:
    orders = (
        select(
            Order.customer_id,
            func.sum(Order.total).label("ordered"),
            func.count(Order.id).label("count"),
        )
        .where(Order.state != "CANCELLED")
        .group_by(Order.customer_id)
        .subquery()
    )
    payments = _net_payments_subquery()
    stmt = (
        select(
            Customer,
            func.coalesce(orders.c.ordered, 0),
            func.coalesce(payments.c.net_paid, 0),
            func.coalesce(orders.c.count, 0),
        )
        .outerjoin(orders, orders.c.customer_id == Customer.id)
        .outerjoin(payments, payments.c.customer_id == Customer.id)
        .order_by(Customer.name)
        .limit(limit)
    )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Customer.name.ilike(pattern), Customer.code.ilike(pattern),
                Customer.phone.ilike(pattern))
        )

    return [
        CustomerRow(
            id=customer.id, code=customer.code, name=customer.name,
            phone=customer.phone, price_tier=customer.price_tier,
            credit_limit=customer.credit_limit,
            debt=int(ordered) - int(paid), order_count=int(count),
            is_active=customer.is_active,
        )
        for customer, ordered, paid, count in session.execute(stmt).all()
    ]


def customer_debt(session: Session, customer_id: str) -> int:
    """Mijoz qarzi = buyurtmalar summasi - sof to'lovlar."""
    ordered = session.execute(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.customer_id == customer_id, Order.state != "CANCELLED"
        )
    ).scalar_one()
    paid = session.execute(
        select(func.coalesce(func.sum(
            case((Payment.direction == "IN", Payment.amount), else_=-Payment.amount)
        ), 0)).where(Payment.customer_id == customer_id)
    ).scalar_one()
    return int(ordered) - int(paid)


# --- buyurtmalar ----------------------------------------------------------


def list_orders(
    session: Session, *, search: str = "", state: str | None = None, limit: int = 500
) -> list[OrderRow]:
    lines = (
        select(OrderLine.order_id, func.count(OrderLine.id).label("count"))
        .group_by(OrderLine.order_id)
        .subquery()
    )
    stmt = (
        select(Order, Customer.name, func.coalesce(lines.c.count, 0))
        .join(Customer, Customer.id == Order.customer_id)
        .outerjoin(lines, lines.c.order_id == Order.id)
        .order_by(Order.ordered_at.desc())
        .limit(limit)
    )
    if state:
        stmt = stmt.where(Order.state == state)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Order.number.ilike(pattern), Customer.name.ilike(pattern)))

    rows = session.execute(stmt).all()

    # Yetkazilish holati FAQAT ko'rsatilayotgan buyurtmalar uchun so'raladi.
    # Avval butun `event_log` bo'yicha so'rov ketardi va 50 000 buyurtmada
    # ro'yxat 382 ms ga cho'zilardi — hozir esa 300 ta ID bo'yicha.
    order_ids = [order.id for order, _name, _count in rows]
    delivery_states: dict[str, str] = {}
    if order_ids:
        delivery_states = dict(
            session.execute(
                select(EventLog.aggregate_id, OutboxEntry.state)
                .join(OutboxEntry, OutboxEntry.event_id == EventLog.event_id)
                .where(
                    # `aggregate_type` SHART: `ix_event_aggregate` indeksi
                    # (aggregate_type, aggregate_id) ustida. Faqat
                    # `event_type` bo'yicha filtrlanganda indeks ishlamaydi
                    # va 1 million hodisa to'liq skan qilinadi.
                    EventLog.aggregate_type == "Order",
                    EventLog.event_type == "ORDER_CREATED",
                    EventLog.aggregate_id.in_(order_ids),
                )
            ).all()
        )

    return [
        OrderRow(
            id=order.id, number=order.number, customer_name=name,
            state=order.state, ordered_at=order.ordered_at, total=order.total,
            paid_total=order.paid_total, line_count=int(count),
            delivery_state=delivery_states.get(order.id, DeliveryState.PEER_APPLIED),
        )
        for order, name, count in rows
    ]


def order_lines(session: Session, order_id: str) -> list[tuple[str, str, Decimal, int, int]]:
    rows = session.execute(
        select(OrderLine, Product.sku, Product.name)
        .join(Product, Product.id == OrderLine.product_id)
        .where(OrderLine.order_id == order_id)
    ).all()
    return [
        (sku, name, Decimal(str(line.quantity)), line.unit_price, line.line_total)
        for line, sku, name in rows
    ]


# --- ombor ----------------------------------------------------------------


def list_stock(session: Session, *, only_below_minimum: bool = False) -> list[StockRow]:
    stmt = (
        select(StockSnapshot, Warehouse.name, Product.sku, Product.name, Product.min_stock)
        .join(Warehouse, Warehouse.id == StockSnapshot.warehouse_id)
        .join(Product, Product.id == StockSnapshot.product_id)
        .order_by(Product.name)
    )
    rows = [
        StockRow(
            warehouse_name=warehouse_name, product_sku=sku, product_name=name,
            quantity=Decimal(str(snapshot.quantity)),
            reserved=Decimal(str(snapshot.reserved)),
            min_stock=Decimal(str(min_stock)),
        )
        for snapshot, warehouse_name, sku, name, min_stock in session.execute(stmt).all()
    ]
    if only_below_minimum:
        rows = [row for row in rows if row.below_minimum]
    return rows


def list_movements(session: Session, *, limit: int = 300) -> list[tuple]:
    return list(session.execute(
        select(
            InventoryMovement.occurred_at, Warehouse.name, Product.sku,
            Product.name, InventoryMovement.movement_type, InventoryMovement.quantity,
        )
        .join(Warehouse, Warehouse.id == InventoryMovement.warehouse_id)
        .join(Product, Product.id == InventoryMovement.product_id)
        .order_by(InventoryMovement.occurred_at.desc())
        .limit(limit)
    ).all())


def list_warehouses(session: Session) -> list[tuple[str, str, str]]:
    return [
        (warehouse.id, warehouse.code, warehouse.name)
        for warehouse in session.execute(
            select(Warehouse).where(Warehouse.is_active.is_(True)).order_by(Warehouse.name)
        ).scalars()
    ]


# --- moliya ---------------------------------------------------------------


def list_payments(session: Session, *, limit: int = 300) -> list[PaymentRow]:
    rows = session.execute(
        select(Payment, Customer.name)
        .outerjoin(Customer, Customer.id == Payment.customer_id)
        .order_by(Payment.occurred_at.desc())
        .limit(limit)
    ).all()
    return [
        PaymentRow(
            id=payment.id, number=payment.number, direction=payment.direction,
            customer_name=name or "—", amount=payment.amount, method=payment.method,
            occurred_at=payment.occurred_at, is_reversed=payment.is_reversed,
        )
        for payment, name in rows
    ]


# --- sinxronizatsiya ------------------------------------------------------


def list_devices(session: Session) -> list[DeviceRow]:
    return [
        DeviceRow(
            device_id=peer.device_id, display_name=peer.display_name,
            platform=peer.platform, role=peer.role, state=peer.state,
            last_seen_at=peer.last_seen_at,
            last_applied_sequence=peer.last_applied_sequence,
            is_full_replica=peer.is_full_replica,
        )
        for peer in session.execute(
            select(PeerDevice).order_by(PeerDevice.display_name)
        ).scalars()
    ]


def list_conflicts(session: Session, *, only_open: bool = True) -> list[ConflictRow]:
    stmt = select(ConflictRecord).order_by(ConflictRecord.detected_at.desc())
    if only_open:
        stmt = stmt.where(ConflictRecord.status == "NEEDS_REVIEW")
    return [
        ConflictRow(
            id=record.id, aggregate_type=record.aggregate_type,
            aggregate_id=record.aggregate_id, field_name=record.field_name,
            strategy=record.strategy, status=record.status,
            resolution=record.resolution, local_value=record.local_value,
            remote_value=record.remote_value, detected_at=record.detected_at,
        )
        for record in session.execute(stmt).scalars()
    ]


def list_dead_letters(session: Session, *, limit: int = 200) -> list[tuple]:
    return list(session.execute(
        select(
            DeadLetter.occurred_at, DeadLetter.channel, DeadLetter.reason,
            DeadLetter.detail, DeadLetter.raw_size_bytes,
        )
        .where(DeadLetter.resolved_at.is_(None))
        .order_by(DeadLetter.occurred_at.desc())
        .limit(limit)
    ).all())


def list_outbox(session: Session, *, limit: int = 200) -> list[tuple]:
    return list(session.execute(
        select(
            OutboxEntry.created_at, EventLog.event_type, OutboxEntry.state,
            OutboxEntry.attempts, OutboxEntry.last_error,
        )
        .join(EventLog, EventLog.event_id == OutboxEntry.event_id)
        .order_by(OutboxEntry.id.desc())
        .limit(limit)
    ).all())


def sync_summary(session: Session) -> SyncSummary:
    queued = session.execute(
        select(func.count()).select_from(OutboxEntry).where(
            OutboxEntry.state.notin_((DeliveryState.PEER_APPLIED, DeliveryState.DEAD_LETTER))
        )
    ).scalar_one()
    dead = session.execute(
        select(func.count()).select_from(DeadLetter).where(DeadLetter.resolved_at.is_(None))
    ).scalar_one()
    conflicts = session.execute(
        select(func.count()).select_from(ConflictRecord).where(
            ConflictRecord.status == "NEEDS_REVIEW"
        )
    ).scalar_one()
    total_events = session.execute(select(func.count()).select_from(EventLog)).scalar_one()
    unapplied = session.execute(
        select(func.count()).select_from(EventLog).where(EventLog.applied_at.is_(None))
    ).scalar_one()
    active = session.execute(
        select(func.count()).select_from(PeerDevice).where(PeerDevice.state == "ACTIVE")
    ).scalar_one()
    revoked = session.execute(
        select(func.count()).select_from(PeerDevice).where(PeerDevice.state == "REVOKED")
    ).scalar_one()
    last_event = session.execute(select(func.max(EventLog.occurred_at))).scalar()

    return SyncSummary(
        queued=int(queued), dead_letters=int(dead), open_conflicts=int(conflicts),
        total_events=int(total_events), unapplied_events=int(unapplied),
        devices_active=int(active), devices_revoked=int(revoked),
        last_event_at=last_event,
    )


# --- audit ----------------------------------------------------------------


def list_audit(session: Session, *, search: str = "", limit: int = 500) -> list[tuple]:
    stmt = (
        select(AuditLog.occurred_at, AuditLog.action, AuditLog.entity_type,
               AuditLog.entity_id, AuditLog.summary)
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
    )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(AuditLog.action.ilike(pattern), AuditLog.summary.ilike(pattern))
        )
    return list(session.execute(stmt).all())


# --- agent va tashriflar --------------------------------------------------


def list_visits(session: Session, *, limit: int = 300) -> list[tuple]:
    return list(session.execute(
        select(Visit.started_at, Customer.name, Visit.outcome, Visit.note)
        .join(Customer, Customer.id == Visit.customer_id)
        .order_by(Visit.started_at.desc())
        .limit(limit)
    ).all())
