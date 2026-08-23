"""Lokal AI maslahatchi — internetsiz ishlaydigan tavsiyalar.

Qat'iy chegaralar (topshiriq §17):

* AI buyurtmani **yakuniy tasdiqlamaydi**;
* to'lov **yaratmaydi**;
* moliyaviy yozuvni **o'zgartirmaydi**;
* qoldiqni **overwrite qilmaydi**;
* AETHER-Q himoyasini **chetlab o'tmaydi**;
* provider kaliti Android'ga **joylanmaydi**.

Shu sababli bu modul **faqat o'qiydi** va `Suggestion` ro'yxatini
qaytaradi. Hech qanday yozuv amali yo'q — buni tip tizimi ham, test ham
qulflaydi.

Bu yerdagi tahlil statistik: tashqi model kerak emas, ya'ni internetsiz
ham to'liq ishlaydi. Tashqi provider (agar sozlansa) faqat matnli
izohlash uchun ishlatiladi (`ai/provider.py`).
"""

from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from distribos.domain.formatting import money as _money_fmt
from distribos.domain.formatting import quantity as _qty
from distribos.persistence.models import (
    Customer,
    InventoryMovement,
    Order,
    OrderLine,
    Payment,
    Product,
    StockSnapshot,
)


class Severity(enum.IntEnum):
    INFO = 1
    ATTENTION = 2
    URGENT = 3


_SEVERITY_LABEL = {
    Severity.INFO: "Ma'lumot",
    Severity.ATTENTION: "E'tibor",
    Severity.URGENT: "Shoshilinch",
}

_SEVERITY_TONE = {
    Severity.INFO: "progress",
    Severity.ATTENTION: "warning",
    Severity.URGENT: "error",
}


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Bitta tavsiya. Bu AMAL EMAS — foydalanuvchi o'zi qaror qiladi."""

    key: str
    severity: Severity
    title: str
    reason: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None

    @property
    def severity_label(self) -> str:
        return _SEVERITY_LABEL[self.severity]

    @property
    def tone(self) -> str:
        return _SEVERITY_TONE[self.severity]


class LocalAdvisor:
    """Lokal ma'lumotlardan tavsiyalar chiqaradi.

    Bu sinf **hech qachon** yozmaydi: uning barcha metodlari `Session` ni
    faqat `select` uchun ishlatadi.
    """

    def analyse(self, session: Session, *, today: dt.date | None = None) -> list[Suggestion]:
        moment = today or dt.date.today()
        suggestions: list[Suggestion] = []
        suggestions += self.low_stock(session)
        suggestions += self.overdue_debt(session, today=moment)
        suggestions += self.credit_risk(session)
        suggestions += self.slow_moving(session, today=moment)
        suggestions += self.repeat_order_candidates(session, today=moment)
        suggestions += self.anomalies(session)
        suggestions.sort(key=lambda item: (-item.severity, item.title))
        return suggestions

    # --- qoldiq -----------------------------------------------------------

    def low_stock(self, session: Session) -> list[Suggestion]:
        """Minimal qoldiqdan pastga tushgan mahsulotlar."""
        rows = session.execute(
            select(Product.id, Product.sku, Product.name, Product.min_stock,
                   func.coalesce(func.sum(StockSnapshot.quantity), 0))
            .outerjoin(StockSnapshot, StockSnapshot.product_id == Product.id)
            .where(Product.is_active.is_(True), Product.min_stock > 0)
            .group_by(Product.id)
        ).all()

        results = []
        for product_id, sku, name, minimum, quantity in rows:
            on_hand = Decimal(str(quantity or 0))
            threshold = Decimal(str(minimum))
            if on_hand >= threshold:
                continue
            ran_out = on_hand <= 0
            results.append(Suggestion(
                key="low_stock",
                severity=Severity.URGENT if ran_out else Severity.ATTENTION,
                title=f"{name} ({sku}) qoldig'i kam",
                reason=(
                    "Qoldiq tugadi" if ran_out
                    else f"Qoldiq {_qty(on_hand)}, minimal {_qty(threshold)}"
                ),
                action="Xarid buyurtmasini tayyorlang yoki minimal qoldiqni qayta ko'ring",
                entity_type="Product", entity_id=product_id,
            ))
        return results

    # --- qarzdorlik -------------------------------------------------------

    @staticmethod
    def _net_payments():
        """Sof to'lov (IN - OUT). Bekor qilinganlar teskari yozuv bilan yopiladi."""
        return (
            select(
                Payment.customer_id.label("customer_id"),
                func.sum(
                    case((Payment.direction == "IN", Payment.amount),
                         else_=-Payment.amount)
                ).label("net_paid"),
            )
            .where(Payment.customer_id.is_not(None))
            .group_by(Payment.customer_id)
            .subquery()
        )

    def overdue_debt(self, session: Session, *, today: dt.date) -> list[Suggestion]:
        payments = self._net_payments()
        rows = session.execute(
            select(
                Customer.id, Customer.name,
                func.coalesce(func.sum(Order.total), 0),
                func.coalesce(func.max(payments.c.net_paid), 0),
                func.min(Order.delivery_due),
            )
            .join(Order, Order.customer_id == Customer.id)
            .outerjoin(payments, payments.c.customer_id == Customer.id)
            .where(Order.state != "CANCELLED")
            .group_by(Customer.id)
        ).all()

        results = []
        for customer_id, name, ordered, paid, due in rows:
            debt = int(ordered or 0) - int(paid or 0)
            if debt <= 0 or due is None or due >= today:
                continue
            days = (today - due).days
            results.append(Suggestion(
                key="overdue_debt",
                severity=Severity.URGENT if days > 30 else Severity.ATTENTION,
                title=f"{name} — muddati o'tgan qarz",
                reason=f"{days} kun kechikkan, summa {_money(debt)}",
                action="Mijoz bilan bog'laning yoki yangi jo'natmani to'xtatib turing",
                entity_type="Customer", entity_id=customer_id,
            ))
        return results

    def credit_risk(self, session: Session) -> list[Suggestion]:
        """Kredit limitiga yaqinlashgan mijozlar."""
        payments = self._net_payments()
        rows = session.execute(
            select(
                Customer.id, Customer.name, Customer.credit_limit,
                func.coalesce(func.sum(Order.total), 0),
                func.coalesce(func.max(payments.c.net_paid), 0),
            )
            .outerjoin(Order, (Order.customer_id == Customer.id) & (Order.state != "CANCELLED"))
            .outerjoin(payments, payments.c.customer_id == Customer.id)
            .where(Customer.credit_limit > 0)
            .group_by(Customer.id)
        ).all()

        results = []
        for customer_id, name, limit, ordered, paid in rows:
            debt = int(ordered or 0) - int(paid or 0)
            if debt <= 0:
                continue
            usage = debt / int(limit)
            if usage < 0.8:
                continue
            results.append(Suggestion(
                key="credit_risk",
                severity=Severity.URGENT if usage >= 1 else Severity.ATTENTION,
                title=f"{name} — kredit limiti {'oshgan' if usage >= 1 else 'to`lmoqda'}",
                reason=f"{_money(debt)} / {_money(int(limit))} ({usage * 100:.0f}%)",
                action="Yangi buyurtmadan oldin to'lovni so'rang yoki limitni qayta ko'ring",
                entity_type="Customer", entity_id=customer_id,
            ))
        return results

    # --- assortiment ------------------------------------------------------

    def slow_moving(self, session: Session, *, today: dt.date, days: int = 60) -> list[Suggestion]:
        """Uzoq vaqt sotilmagan, lekin omborda turgan mahsulotlar."""
        cutoff = dt.datetime.combine(today - dt.timedelta(days=days), dt.time.min, dt.UTC)

        recent = set(session.execute(
            select(OrderLine.product_id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(Order.ordered_at >= cutoff)
        ).scalars())

        rows = session.execute(
            select(Product.id, Product.sku, Product.name,
                   func.coalesce(func.sum(StockSnapshot.quantity), 0))
            .outerjoin(StockSnapshot, StockSnapshot.product_id == Product.id)
            .where(Product.is_active.is_(True))
            .group_by(Product.id)
        ).all()

        results = []
        for product_id, sku, name, quantity in rows:
            on_hand = Decimal(str(quantity or 0))
            if product_id in recent or on_hand <= 0:
                continue
            results.append(Suggestion(
                key="slow_moving", severity=Severity.INFO,
                title=f"{name} ({sku}) sekin sotilmoqda",
                reason=f"So'nggi {days} kunda sotilmagan, omborda {_qty(on_hand)} qoldi",
                action="Aksiya taklif qiling yoki xaridni to'xtatib turing",
                entity_type="Product", entity_id=product_id,
            ))
        return results

    def repeat_order_candidates(
        self, session: Session, *, today: dt.date, days: int = 30
    ) -> list[Suggestion]:
        """Odatda muntazam oladigan, lekin uzoq vaqt buyurtma bermagan mijozlar."""
        cutoff = dt.datetime.combine(today - dt.timedelta(days=days), dt.time.min, dt.UTC)

        rows = session.execute(
            select(
                Customer.id, Customer.name,
                func.count(Order.id), func.max(Order.ordered_at),
            )
            .join(Order, Order.customer_id == Customer.id)
            .where(Order.state != "CANCELLED")
            .group_by(Customer.id)
            .having(func.count(Order.id) >= 3)
        ).all()

        results = []
        for customer_id, name, count, last_order in rows:
            if last_order is None:
                continue
            if last_order.tzinfo is None:
                last_order = last_order.replace(tzinfo=dt.UTC)
            if last_order >= cutoff:
                continue
            gap = (dt.datetime.now(dt.UTC) - last_order).days
            results.append(Suggestion(
                key="repeat_order", severity=Severity.ATTENTION,
                title=f"{name} — {gap} kundan beri buyurtma yo'q",
                reason=f"Ilgari {count} marta buyurtma bergan, odatda muntazam mijoz",
                action="Agentga tashrif rejalashtiring yoki qo'ng'iroq qiling",
                entity_type="Customer", entity_id=customer_id,
            ))
        return results

    # --- anomaliyalar -----------------------------------------------------

    def anomalies(self, session: Session) -> list[Suggestion]:
        """Odatdan tashqari holatlar — soxta emas, tekshirishga arziydi."""
        results: list[Suggestion] = []

        # Manfiy qoldiq — ombor hisobida xato bo'lishi mumkin.
        negative = session.execute(
            select(Product.sku, Product.name, StockSnapshot.quantity)
            .join(Product, Product.id == StockSnapshot.product_id)
            .where(StockSnapshot.quantity < 0)
        ).all()
        for sku, name, quantity in negative:
            results.append(Suggestion(
                key="negative_stock", severity=Severity.URGENT,
                title=f"{name} ({sku}) qoldig'i manfiy",
                reason=f"Hisoblangan qoldiq {_qty(quantity)}",
                action="Ombor harakatlarini tekshiring — kirim yozilmagan bo'lishi mumkin",
            ))

        # Katta chegirma — narx siyosati buzilgan bo'lishi mumkin.
        big_discounts = session.execute(
            select(func.count()).select_from(OrderLine)
            .where(OrderLine.discount_percent > 30)
        ).scalar_one()
        if big_discounts:
            results.append(Suggestion(
                key="large_discount", severity=Severity.ATTENTION,
                title=f"{big_discounts} ta qatorda 30% dan katta chegirma",
                reason="Katta chegirma foyda marjasini keskin kamaytiradi",
                action="Hisobotlar > Foyda marjasi bo'limidan tekshiring",
            ))

        # Bekor qilingan to'lovlar ko'p bo'lsa.
        reversed_count = session.execute(
            select(func.count()).select_from(Payment).where(Payment.is_reversed.is_(True))
        ).scalar_one()
        total_payments = session.execute(
            select(func.count()).select_from(Payment)
        ).scalar_one()
        if total_payments >= 10 and reversed_count / total_payments > 0.1:
            results.append(Suggestion(
                key="many_reversals", severity=Severity.ATTENTION,
                title=f"To'lovlarning {reversed_count / total_payments:.0%} i bekor qilingan",
                reason=f"{reversed_count} ta bekor qilingan to'lov",
                action="Kassa jarayonini ko'rib chiqing — xatolar takrorlanmoqda",
            ))

        # Hisobdan chiqarish ko'p bo'lsa.
        write_offs = session.execute(
            select(func.count()).select_from(InventoryMovement)
            .where(InventoryMovement.movement_type == "WRITE_OFF")
        ).scalar_one()
        if write_offs >= 10:
            results.append(Suggestion(
                key="many_write_offs", severity=Severity.INFO,
                title=f"{write_offs} ta hisobdan chiqarish yozuvi",
                reason="Yo'qotishlar foydaga bevosita ta'sir qiladi",
                action="Sabablarini tahlil qiling (yaroqlilik muddati, shikast)",
            ))

        return results


def _money(amount: int) -> str:
    return _money_fmt(amount)
