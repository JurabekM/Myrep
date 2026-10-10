"""Savat mantig'i (Qt'siz). Narx klientda ko'rsatish uchun; yakuniy summani server qayta hisoblaydi."""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .money import round_som

ZERO = Decimal("0")


@dataclass
class CartLine:
    product_id: str
    name: str
    unit: str
    unit_price: int
    qty: Decimal

    @property
    def line_total(self) -> int:
        return round_som(self.qty * self.unit_price)


@dataclass
class Cart:
    lines: list[CartLine] = field(default_factory=list)
    discount: int = 0

    def _find(self, product_id: str) -> CartLine | None:
        return next((line for line in self.lines if line.product_id == product_id), None)

    def add(self, product: dict[str, Any], qty: Decimal = Decimal(1)) -> CartLine:
        if qty <= ZERO:
            raise ValueError("Miqdor musbat bo'lishi kerak")
        existing = self._find(product["id"])
        if existing is not None:
            existing.qty += qty
            return existing
        line = CartLine(
            product_id=product["id"],
            name=product["name"],
            unit=product["unit"],
            unit_price=int(product["sale_price"]),
            qty=qty,
        )
        self.lines.append(line)
        return line

    def set_qty(self, product_id: str, qty: Decimal) -> None:
        line = self._find(product_id)
        if line is None:
            raise KeyError(product_id)
        if qty <= ZERO:
            self.remove(product_id)
        else:
            line.qty = qty

    def remove(self, product_id: str) -> None:
        self.lines = [line for line in self.lines if line.product_id != product_id]

    def clear(self) -> None:
        self.lines = []
        self.discount = 0

    @property
    def is_empty(self) -> bool:
        return not self.lines

    @property
    def subtotal(self) -> int:
        return sum(line.line_total for line in self.lines)

    @property
    def total(self) -> int:
        return max(self.subtotal - self.discount, 0)

    def set_discount(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Chegirma manfiy bo'lishi mumkin emas")
        if amount > self.subtotal:
            raise ValueError("Chegirma jami summadan katta bo'lishi mumkin emas")
        self.discount = amount

    def to_sale_payload(
        self, store_id: str, payments: list[tuple[str, int]], sale_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        """Backend'ga yuboriladigan savdo. Narx yuborilmaydi — faqat tovar va miqdor."""
        return {
            "id": str(sale_id or uuid.uuid4()),
            "store_id": store_id,
            "items": [{"product_id": line.product_id, "qty": str(line.qty)} for line in self.lines],
            "discount": self.discount,
            "payments": [{"method": method, "amount": amount} for method, amount in payments],
        }
