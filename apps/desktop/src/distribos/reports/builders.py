"""Hisobotlar — ma'lumot yig'ish va eksport.

Dashboard emas: har hisobot filtrlanadigan jadval bo'lib, CSV yoki PDF
sifatida eksport qilinadi.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from distribos.domain.formatting import money as _money_fmt
from distribos.domain.formatting import quantity as _qty
from distribos.persistence.models import (
    ConflictRecord,
    Customer,
    DeadLetter,
    InventoryMovement,
    Order,
    OrderLine,
    Payment,
    PeerDevice,
    Product,
    StockSnapshot,
    User,
    Warehouse,
)


@dataclass(slots=True)
class Report:
    """Tayyor hisobot: sarlavha, ustunlar, qatorlar."""

    key: str
    title: str
    description: str
    columns: Sequence[str]
    rows: list[Sequence[object]] = field(default_factory=list)
    generated_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC))
    #: Pastdagi yakuniy qator (jami), bo'lsa.
    footer: Sequence[object] | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def to_csv(self, path: Path) -> Path:
        """CSV eksport. Excel o'zbekcha harflarni to'g'ri o'qishi uchun BOM."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(self.columns)
            writer.writerows(self.rows)
            if self.footer:
                writer.writerow(self.footer)
        return path


def _money(value: object) -> str:
    return _money_fmt(int(value or 0))


def _period(start: dt.date | None, end: dt.date | None) -> str:
    if start and end:
        return f"{start:%d.%m.%Y} — {end:%d.%m.%Y}"
    if start:
        return f"{start:%d.%m.%Y} dan"
    if end:
        return f"{end:%d.%m.%Y} gacha"
    return "Butun davr"


def daily_sales(
    session: Session, *, start: dt.date | None = None, end: dt.date | None = None
) -> Report:
    stmt = (
        select(
            func.date(Order.ordered_at).label("day"),
            func.count(Order.id),
            func.sum(Order.total),
            func.sum(Order.paid_total),
        )
        .where(Order.state != "CANCELLED")
        .group_by("day")
        .order_by("day")
    )
    stmt = _apply_dates(stmt, Order.ordered_at, start, end)

    rows: list[Sequence[object]] = []
    total_sum = total_paid = 0
    for day, count, amount, paid in session.execute(stmt).all():
        total_sum += int(amount or 0)
        total_paid += int(paid or 0)
        rows.append((day, count, _money(amount), _money(paid),
                     _money(int(amount or 0) - int(paid or 0))))

    return Report(
        key="daily_sales", title="Kunlik savdo",
        description=f"Davr: {_period(start, end)}",
        columns=["Sana", "Buyurtmalar", "Summa", "To'langan", "Qarz"],
        rows=rows,
        footer=("JAMI", sum(int(r[1]) for r in rows), _money(total_sum),
                _money(total_paid), _money(total_sum - total_paid)),
    )


def sales_by_product(
    session: Session, *, start: dt.date | None = None, end: dt.date | None = None
) -> Report:
    stmt = (
        select(
            Product.sku, Product.name,
            func.sum(OrderLine.quantity), func.sum(OrderLine.line_total),
        )
        .join(OrderLine, OrderLine.product_id == Product.id)
        .join(Order, Order.id == OrderLine.order_id)
        .where(Order.state != "CANCELLED")
        .group_by(Product.id)
        .order_by(func.sum(OrderLine.line_total).desc())
    )
    stmt = _apply_dates(stmt, Order.ordered_at, start, end)

    rows = [
        (sku, name, _qty(quantity or 0), _money(amount))
        for sku, name, quantity, amount in session.execute(stmt).all()
    ]
    return Report(
        key="sales_by_product", title="Mahsulot bo'yicha savdo",
        description=f"Davr: {_period(start, end)}",
        columns=["SKU", "Mahsulot", "Sotilgan", "Summa"], rows=rows,
    )


def sales_by_customer(
    session: Session, *, start: dt.date | None = None, end: dt.date | None = None
) -> Report:
    # `Order.paid_total` emas, HAQIQIY to'lovlar: mijoz ko'pincha umumiy
    # summani hisobga to'laydi va uni buyurtmaga biriktirmaydi.
    payments = _net_payments()
    stmt = (
        select(
            Customer.code, Customer.name, func.count(Order.id),
            func.sum(Order.total),
            func.coalesce(func.max(payments.c.net_paid), 0),
        )
        .join(Order, Order.customer_id == Customer.id)
        .outerjoin(payments, payments.c.customer_id == Customer.id)
        .where(Order.state != "CANCELLED")
        .group_by(Customer.id)
        .order_by(func.sum(Order.total).desc())
    )
    stmt = _apply_dates(stmt, Order.ordered_at, start, end)

    rows = [
        (code, name, count, _money(total), _money(paid),
         _money(int(total or 0) - int(paid or 0)))
        for code, name, count, total, paid in session.execute(stmt).all()
    ]
    return Report(
        key="sales_by_customer", title="Mijoz bo'yicha savdo",
        description=f"Davr: {_period(start, end)}",
        columns=["Kod", "Mijoz", "Buyurtmalar", "Summa", "To'langan", "Qarz"],
        rows=rows,
    )


def sales_by_agent(
    session: Session, *, start: dt.date | None = None, end: dt.date | None = None
) -> Report:
    stmt = (
        select(User.full_name, func.count(Order.id), func.sum(Order.total))
        .join(Order, Order.agent_id == User.id)
        .where(Order.state != "CANCELLED")
        .group_by(User.id)
        .order_by(func.sum(Order.total).desc())
    )
    stmt = _apply_dates(stmt, Order.ordered_at, start, end)
    rows = [
        (name, count, _money(total))
        for name, count, total in session.execute(stmt).all()
    ]
    return Report(
        key="sales_by_agent", title="Agent bo'yicha savdo",
        description=f"Davr: {_period(start, end)}",
        columns=["Agent", "Buyurtmalar", "Summa"], rows=rows,
    )


def stock_report(session: Session, *, only_below_minimum: bool = False) -> Report:
    rows_data = session.execute(
        select(
            Warehouse.name, Product.sku, Product.name,
            StockSnapshot.quantity, StockSnapshot.reserved, Product.min_stock,
        )
        .join(StockSnapshot, StockSnapshot.warehouse_id == Warehouse.id)
        .join(Product, Product.id == StockSnapshot.product_id)
        .order_by(Warehouse.name, Product.name)
    ).all()

    rows: list[Sequence[object]] = []
    for warehouse, sku, name, quantity, reserved, minimum in rows_data:
        available = Decimal(str(quantity)) - Decimal(str(reserved))
        below = Decimal(str(minimum)) > 0 and Decimal(str(quantity)) < Decimal(str(minimum))
        if only_below_minimum and not below:
            continue
        rows.append((
            warehouse, sku, name,
            _qty(quantity), _qty(reserved), _qty(available), _qty(minimum),
            "Kam qoldi" if below else "",
        ))

    return Report(
        key="stock" if not only_below_minimum else "stock_low",
        title="Minimal qoldiq" if only_below_minimum else "Ombor qoldig'i",
        description="Qoldiq harakatlar jurnalidan hisoblangan",
        columns=["Ombor", "SKU", "Mahsulot", "Qoldiq", "Rezerv", "Mavjud",
                 "Minimal", "Izoh"],
        rows=rows,
    )


def _net_payments():
    """Mijoz bo'yicha sof to'lov (IN - OUT).

    Bekor qilingan to'lov teskari yozuv bilan o'z-o'zidan nolga chiqadi.
    """
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


def debt_report(session: Session, *, only_overdue: bool = False) -> Report:
    payments = _net_payments()
    stmt = (
        select(
            Customer.code, Customer.name, Customer.phone, Customer.credit_limit,
            func.coalesce(func.sum(Order.total), 0),
            func.coalesce(func.max(payments.c.net_paid), 0),
            func.min(Order.delivery_due),
        )
        .outerjoin(Order, (Order.customer_id == Customer.id) & (Order.state != "CANCELLED"))
        .outerjoin(payments, payments.c.customer_id == Customer.id)
        .group_by(Customer.id)
        .order_by(Customer.name)
    )

    today = dt.date.today()
    rows: list[Sequence[object]] = []
    total_debt = 0
    for code, name, phone, limit, ordered, paid, due in session.execute(stmt).all():
        debt = int(ordered or 0) - int(paid or 0)
        if debt <= 0:
            continue
        overdue = bool(due and due < today)
        if only_overdue and not overdue:
            continue
        total_debt += debt
        rows.append((
            code, name, phone or "—",
            _money(limit) if limit else "Cheklanmagan", _money(debt),
            "Muddati o'tgan" if overdue else "",
        ))

    return Report(
        key="overdue_debt" if only_overdue else "debt",
        title="Muddati o'tgan qarzlar" if only_overdue else "Qarzdorlik",
        description=f"Jami: {_money(total_debt)}",
        columns=["Kod", "Mijoz", "Telefon", "Kredit limiti", "Qarz", "Izoh"],
        rows=rows,
        footer=("JAMI", "", "", "", _money(total_debt), ""),
    )


def cash_flow(
    session: Session, *, start: dt.date | None = None, end: dt.date | None = None
) -> Report:
    stmt = (
        select(
            func.date(Payment.occurred_at),
            Payment.direction,
            func.count(Payment.id),
            func.sum(Payment.amount),
        )
        .where(Payment.is_reversed.is_(False))
        .group_by(func.date(Payment.occurred_at), Payment.direction)
        .order_by(func.date(Payment.occurred_at))
    )
    stmt = _apply_dates(stmt, Payment.occurred_at, start, end)

    rows = [
        (day, "Kirim" if direction == "IN" else "Chiqim", count, _money(amount))
        for day, direction, count, amount in session.execute(stmt).all()
    ]
    return Report(
        key="cash_flow", title="Kassa harakatlari",
        description=f"Davr: {_period(start, end)} (bekor qilinganlar hisobga olinmagan)",
        columns=["Sana", "Yo'nalish", "Soni", "Summa"], rows=rows,
    )


def profit_margin(
    session: Session, *, start: dt.date | None = None, end: dt.date | None = None
) -> Report:
    """Foyda marjasi — sotuv narxi va xarid narxi farqi.

    DIQQAT: xarid narxi katalogdagi JORIY qiymat. Aniq marja uchun
    partiya bo'yicha tannarx kerak — bu keyingi bosqichda.
    """
    stmt = (
        select(
            Product.sku, Product.name,
            func.sum(OrderLine.quantity),
            func.sum(OrderLine.line_total),
            Product.purchase_price,
        )
        .join(OrderLine, OrderLine.product_id == Product.id)
        .join(Order, Order.id == OrderLine.order_id)
        .where(Order.state != "CANCELLED")
        .group_by(Product.id)
    )
    stmt = _apply_dates(stmt, Order.ordered_at, start, end)

    rows: list[Sequence[object]] = []
    for sku, name, quantity, revenue, cost_price in session.execute(stmt).all():
        sold = Decimal(str(quantity or 0))
        cost = int(cost_price or 0) * sold
        margin = Decimal(int(revenue or 0)) - cost
        percent = (margin / Decimal(int(revenue))) * 100 if revenue else Decimal(0)
        rows.append((
            sku, name, _qty(sold), _money(revenue),
            _money(int(cost)), _money(int(margin)), f"{percent:.1f} %",
        ))

    rows.sort(key=lambda row: row[0])
    return Report(
        key="profit_margin", title="Foyda marjasi",
        description=(
            f"Davr: {_period(start, end)}. Tannarx katalogdagi joriy xarid "
            "narxi bo'yicha hisoblangan."
        ),
        columns=["SKU", "Mahsulot", "Sotilgan", "Tushum", "Tannarx",
                 "Foyda", "Marja"],
        rows=rows,
    )


def returns_report(session: Session) -> Report:
    rows = [
        (occurred.strftime("%d.%m.%Y"), warehouse, sku, name,
         _qty(quantity))
        for occurred, warehouse, sku, name, quantity in session.execute(
            select(
                InventoryMovement.occurred_at, Warehouse.name,
                Product.sku, Product.name, InventoryMovement.quantity,
            )
            .join(Warehouse, Warehouse.id == InventoryMovement.warehouse_id)
            .join(Product, Product.id == InventoryMovement.product_id)
            .where(InventoryMovement.movement_type.in_(("RETURN_IN", "RETURN_OUT")))
            .order_by(InventoryMovement.occurred_at.desc())
        ).all()
    ]
    return Report(
        key="returns", title="Qaytarishlar", description="Ombor jurnalidan",
        columns=["Sana", "Ombor", "SKU", "Mahsulot", "Miqdor"], rows=rows,
    )


def sync_errors(session: Session) -> Report:
    from distribos.presentation.status import rejection_status

    rows = [
        (occurred.strftime("%d.%m.%Y %H:%M"), channel,
         rejection_status(reason).text, detail or "", size)
        for occurred, channel, reason, detail, size in session.execute(
            select(
                DeadLetter.occurred_at, DeadLetter.channel, DeadLetter.reason,
                DeadLetter.detail, DeadLetter.raw_size_bytes,
            ).order_by(DeadLetter.occurred_at.desc())
        ).all()
    ]
    return Report(
        key="sync_errors", title="Sinxronizatsiya xatolari",
        description="Qabul qilinmagan yoki yuborilmagan xabarlar",
        columns=["Vaqt", "Kanal", "Sabab", "Tafsilot", "Hajm"], rows=rows,
    )


def conflicts_report(session: Session) -> Report:
    rows = [
        (record.detected_at.strftime("%d.%m.%Y %H:%M"), record.aggregate_type,
         record.aggregate_id[:12], record.strategy, record.status,
         record.resolution or "")
        for record in session.execute(
            select(ConflictRecord).order_by(ConflictRecord.detected_at.desc())
        ).scalars()
    ]
    return Report(
        key="conflicts", title="Konfliktlar",
        description="Avtomatik hal qilingan va tekshiruv kutayotgan holatlar",
        columns=["Vaqt", "Nima", "Yozuv", "Qoida", "Holat", "Izoh"], rows=rows,
    )


def device_security(session: Session) -> Report:
    rows = [
        (peer.display_name, peer.platform, peer.role, peer.state,
         peer.last_seen_at.strftime("%d.%m.%Y %H:%M") if peer.last_seen_at else "—",
         peer.revoked_reason or "")
        for peer in session.execute(
            select(PeerDevice).order_by(PeerDevice.display_name)
        ).scalars()
    ]
    return Report(
        key="device_security", title="Qurilma xavfsizlik holati",
        description="Ro'yxatdagi barcha qurilmalar",
        columns=["Nomi", "Turi", "Rol", "Holat", "Oxirgi aloqa", "Bekor sababi"],
        rows=rows,
    )


def _apply_dates(stmt, column, start: dt.date | None, end: dt.date | None):
    if start:
        stmt = stmt.where(column >= dt.datetime.combine(start, dt.time.min, dt.UTC))
    if end:
        stmt = stmt.where(column <= dt.datetime.combine(end, dt.time.max, dt.UTC))
    return stmt


#: UI'da ko'rsatiladigan hisobotlar ro'yxati.
AVAILABLE_REPORTS: tuple[tuple[str, str, object], ...] = (
    ("daily_sales", "Kunlik savdo", daily_sales),
    ("sales_by_product", "Mahsulot bo'yicha savdo", sales_by_product),
    ("sales_by_customer", "Mijoz bo'yicha savdo", sales_by_customer),
    ("sales_by_agent", "Agent bo'yicha savdo", sales_by_agent),
    ("stock", "Ombor qoldig'i", stock_report),
    ("stock_low", "Minimal qoldiq", lambda s, **k: stock_report(s, only_below_minimum=True)),
    ("debt", "Qarzdorlik", debt_report),
    ("overdue_debt", "Muddati o'tgan qarzlar", lambda s, **k: debt_report(s, only_overdue=True)),
    ("cash_flow", "Kassa harakatlari", cash_flow),
    ("returns", "Qaytarishlar", lambda s, **k: returns_report(s)),
    ("profit_margin", "Foyda marjasi", profit_margin),
    ("sync_errors", "Sinxronizatsiya xatolari", lambda s, **k: sync_errors(s)),
    ("conflicts", "Konfliktlar", lambda s, **k: conflicts_report(s)),
    ("device_security", "Qurilma xavfsizlik holati", lambda s, **k: device_security(s)),
)
