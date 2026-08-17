# -*- coding: utf-8 -*-
"""
Xarid servisi.

Hayot sikli: ``draft`` -> ``received`` (ombor kirimi + o'rtacha tannarx
yangilanadi) -> ``paid``/``partial`` (to'lovlar 3-bosqichda buxgalteriya
bilan bog'lanadi). Bekor qilinganda ombor kirimi teskari qaytariladi.

Narxlar QQS bilan kiritiladi (QQS ichida hisoblanadi).
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, StateError, ValidationError
from src.core.utils import D, next_document_number, now_str, Page, clamp_page, today_str
from src.modules.base import BaseService


class PurchaseService(BaseService):
    """Xarid hujjatlarini boshqaruvchi servis."""

    # ------------------------------------------------------------------ #
    #  Yaratish / o'qish
    # ------------------------------------------------------------------ #

    def create(self, supplier_id: int | None, warehouse_id: int,
               items: list[dict], user: dict | None = None,
               note: str = "", doc_date: str | None = None) -> int:
        """
        Yangi xarid hujjati (qoralama).

        ``items``: ``[{"product_id": 1, "quantity": 5, "price": 12000}, ...]``
        Narx QQS bilan; QQS summasi mahsulot stavkasidan ajratib olinadi.
        """
        lines = self._build_lines(items)
        subtotal = D(sum((line["total"] for line in lines), Decimal("0")))
        vat_total = D(sum((line["vat_amount"] for line in lines), Decimal("0")))

        with self.db.transaction():
            number = next_document_number(self.db, "PUR")
            purchase_id = self.db.insert("purchases", {
                "number": number,
                "supplier_id": supplier_id,
                "warehouse_id": warehouse_id,
                "status": "draft",
                "subtotal": subtotal,
                "vat_amount": vat_total,
                "total": subtotal,
                "paid_amount": 0,
                "note": note,
                "user_id": user.get("id") if user else None,
                "doc_date": doc_date or today_str(),
                "created_at": now_str(),
                "updated_at": now_str(),
            })
            for line in lines:
                line["purchase_id"] = purchase_id
                self.db.insert("purchase_items", line)

        self.audit.log("purchase.create", user=user, entity="purchase",
                       entity_id=purchase_id, details=f"{number}, {len(lines)} pozitsiya")
        return purchase_id

    def get(self, purchase_id: int) -> dict:
        """Hujjat + pozitsiyalari + ta'minotchi nomi."""
        doc = self.db.query_one(
            "SELECT pu.*, s.name AS supplier_name FROM purchases pu "
            "LEFT JOIN suppliers s ON s.id = pu.supplier_id "
            "WHERE pu.id = ?", (purchase_id,)
        )
        if not doc:
            raise NotFoundError(f"Xarid topilmadi (id={purchase_id}).")
        items = self.db.query(
            "SELECT i.*, p.name AS product_name, p.unit, p.sku "
            "FROM purchase_items i JOIN products p ON p.id = i.product_id "
            "WHERE i.purchase_id = ? ORDER BY i.id", (purchase_id,)
        )
        return {"doc": doc, "items": items}

    def list_purchases(self, page: int = 1, per_page: int = 25,
                       status: str | None = None,
                       search: str | None = None) -> Page:
        """Sahifalangan xaridlar ro'yxati."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if status:
            where.append("pu.status = ?")
            params.append(status)
        if search:
            where.append("(pu.number LIKE ? OR s.name LIKE ?)")
            like = f"%{search.strip()}%"
            params += [like, like]
        cond = " AND ".join(where)
        base = ("FROM purchases pu LEFT JOIN suppliers s "
                "ON s.id = pu.supplier_id WHERE " + cond)
        total = int(self.db.scalar(f"SELECT COUNT(*) {base}", tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT pu.*, s.name AS supplier_name {base} "
            f"ORDER BY pu.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    # ------------------------------------------------------------------ #
    #  Holat o'zgarishlari
    # ------------------------------------------------------------------ #

    def receive(self, purchase_id: int, user: dict | None = None) -> None:
        """
        Xaridni qabul qiladi: ombor kirimi + o'rtacha tannarx yangilanadi.
        """
        data = self.get(purchase_id)
        doc, items = data["doc"], data["items"]
        if doc["status"] != "draft":
            raise StateError("Faqat qoralama xaridni qabul qilish mumkin.")

        inventory = self.container.get("inventory")
        products = self.container.get("products")

        with self.db.transaction():
            for item in items:
                self._update_average_cost(products, item)
                inventory.move_in(
                    item["product_id"], doc["warehouse_id"],
                    D(item["quantity"]), unit_cost=D(item["price"]),
                    ref_type="purchase", ref_id=purchase_id,
                    note=doc["number"], user=user,
                )
            self.db.update("purchases", {
                "status": "received", "updated_at": now_str(),
            }, "id = ?", (purchase_id,))

        self.audit.log("purchase.receive", user=user, entity="purchase",
                       entity_id=purchase_id, details=doc["number"])
        self.bus.emit("purchase.received", purchase_id=purchase_id,
                      total=D(doc["total"]),
                      user_id=user.get("id") if user else None)

    def cancel(self, purchase_id: int, user: dict | None = None) -> None:
        """Xaridni bekor qiladi (qabul qilingan bo'lsa kirim teskari qaytariladi)."""
        data = self.get(purchase_id)
        doc, items = data["doc"], data["items"]
        if doc["status"] == "cancelled":
            raise StateError("Xarid allaqachon bekor qilingan.")
        if D(doc["paid_amount"]) > 0:
            raise StateError("To'lov qilingan xaridni bekor qilib bo'lmaydi.")

        inventory = self.container.get("inventory")
        with self.db.transaction():
            if doc["status"] == "received":
                for item in items:
                    inventory.move_out(
                        item["product_id"], doc["warehouse_id"],
                        D(item["quantity"]), ref_type="purchase_cancel",
                        ref_id=purchase_id, note=doc["number"], user=user,
                    )
            self.db.update("purchases", {
                "status": "cancelled", "updated_at": now_str(),
            }, "id = ?", (purchase_id,))
        self.audit.log("purchase.cancel", user=user, entity="purchase",
                       entity_id=purchase_id, details=doc["number"])

    def register_payment(self, purchase_id: int, amount,
                         user: dict | None = None) -> None:
        """
        To'lov summasini hujjatga qayd etadi (kassa/bank yozuvi 3-bosqichdagi
        PaymentService orqali amalga oshiriladi).
        """
        doc = self.get(purchase_id)["doc"]
        if doc["status"] not in ("received", "partial"):
            raise StateError("Faqat qabul qilingan xaridga to'lov qilish mumkin.")
        pay = D(amount)
        if pay <= 0:
            raise ValidationError("To'lov summasi musbat bo'lishi kerak.")
        remaining = D(doc["total"]) - D(doc["paid_amount"])
        if pay > remaining:
            raise ValidationError(
                f"To'lov qoldiq qarzdan oshib ketdi (qoldiq: {remaining}).")
        new_paid = D(doc["paid_amount"]) + pay
        status = "paid" if new_paid >= D(doc["total"]) else "partial"
        self.db.update("purchases", {
            "paid_amount": new_paid, "status": status, "updated_at": now_str(),
        }, "id = ?", (purchase_id,))
        self.bus.emit("purchase.payment", purchase_id=purchase_id,
                      amount=pay, user_id=user.get("id") if user else None)

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _build_lines(self, items: list[dict]) -> list[dict]:
        """Pozitsiyalarni tekshiradi va summalarini hisoblaydi."""
        if not items:
            raise ValidationError("Xaridda kamida bitta pozitsiya bo'lishi kerak.")
        lines = []
        for raw in items:
            product = self.db.query_one(
                "SELECT * FROM products WHERE id = ? AND is_active = 1",
                (raw.get("product_id"),),
            )
            if not product:
                raise NotFoundError(
                    f"Mahsulot topilmadi (id={raw.get('product_id')}).")
            qty = D(raw.get("quantity"))
            if qty <= 0:
                raise ValidationError(f"{product['name']}: miqdor musbat bo'lsin.")
            price = D(raw.get("price", product["cost_price"]))
            if price < 0:
                raise ValidationError(f"{product['name']}: narx manfiy bo'lmasin.")
            vat_rate = D(raw.get("vat_rate", product["vat_rate"]))
            total = D(qty * price)
            vat_amount = D(total * vat_rate / (100 + vat_rate)) if vat_rate > 0 else D(0)
            lines.append({
                "product_id": product["id"],
                "quantity": qty,
                "price": price,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "total": total,
            })
        return lines

    def _update_average_cost(self, products, item: dict) -> None:
        """
        O'rtacha tannarx usuli (weighted average):

        ``yangi = (eski_qoldiq*eski_narx + kirim*kirim_narx) / (eski_qoldiq+kirim)``
        """
        inventory = self.container.get("inventory")
        product = self.db.query_one(
            "SELECT id, cost_price FROM products WHERE id = ?",
            (item["product_id"],),
        )
        old_qty = inventory.total_stock(item["product_id"])
        old_cost = D(product["cost_price"])
        qty, price = D(item["quantity"]), D(item["price"])
        denominator = old_qty + qty
        if denominator <= 0:
            new_cost = price
        else:
            new_cost = D((old_qty * old_cost + qty * price) / denominator)
        if new_cost != old_cost:
            products.update_cost_price(item["product_id"], new_cost)
