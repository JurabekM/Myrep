# -*- coding: utf-8 -*-
"""
Savdo servisi — hujjatlar hayot siklining yagona markazi.

Hujjat turlari:
  * ``quotation`` — tijorat taklifi (omborga ta'sir qilmaydi)
  * ``order``     — buyurtma (omborga ta'sir qilmaydi, avans olish mumkin)
  * ``invoice``   — hisob-faktura (tasdiqlanganda ombordan chiqim)
  * ``pos``       — kassa savdosi (yaratish + tasdiqlash + to'lov bir qadamda)
  * ``return``    — qaytarish (ombor kirimi, hisobotlarda ayiriladi)

Holatlar: ``draft`` -> ``confirmed`` -> ``partial``/``paid`` (yoki ``cancelled``).
Narxlar QQS BILAN kiritiladi; QQS summasi stavkadan ajratib olinadi.
Chegirma: pozitsiya darajasida (absolyut) va hujjat darajasida (absolyut).
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, StateError, ValidationError
from src.core.utils import (
    D, clamp_page, next_document_number, now_str, Page, today_str,
)
from src.modules.base import BaseService

VALID_TYPES = ("quotation", "order", "invoice", "pos", "return")
_PREFIX = {"quotation": "QUO", "order": "ORD", "invoice": "INV",
           "pos": "POS", "return": "RET"}
#: Ombordan chiqim qilinadigan hujjat turlari
_STOCK_TYPES = ("invoice", "pos")
#: quotation -> order -> invoice konvertatsiya yo'nalishlari
_CONVERT_FLOW = {"quotation": "order", "order": "invoice"}


class SalesService(BaseService):
    """Savdo hujjatlarini boshqaruvchi servis."""

    # ------------------------------------------------------------------ #
    #  Yaratish
    # ------------------------------------------------------------------ #

    def create_doc(self, doc_type: str, customer_id: int | None,
                   warehouse_id: int | None, items: list[dict],
                   user: dict | None = None, note: str = "",
                   discount=0, doc_date: str | None = None,
                   parent_id: int | None = None) -> int:
        """
        Yangi savdo hujjati (qoralama) yaratadi va ``id`` sini qaytaradi.

        ``items``: ``[{"product_id": 1, "quantity": 2, "price": 15000,
        "discount": 0}, ...]`` — narx berilmasa mahsulotning sotish narxi
        olinadi; mijozning shaxsiy chegirma foizi avtomatik qo'llanadi.
        """
        if doc_type not in VALID_TYPES:
            raise ValidationError(f"Noma'lum hujjat turi: {doc_type}")
        customer = self._get_customer(customer_id) if customer_id else None
        lines = self._build_lines(items, customer)
        totals = self._totals(lines, D(discount))

        if doc_type in _STOCK_TYPES and not warehouse_id:
            inventory = self.container.get("inventory")
            warehouse_id = inventory.default_warehouse_id()

        with self.db.transaction():
            number = next_document_number(self.db, _PREFIX[doc_type])
            doc_id = self.db.insert("sales_docs", {
                "doc_type": doc_type,
                "number": number,
                "customer_id": customer_id,
                "warehouse_id": warehouse_id,
                "status": "draft",
                "subtotal": totals["subtotal"],
                "discount": totals["discount"],
                "vat_amount": totals["vat_amount"],
                "total": totals["total"],
                "paid_amount": 0,
                "currency": str(self.config.get("app.currency", "UZS")),
                "note": note,
                "user_id": user.get("id") if user else None,
                "parent_id": parent_id,
                "doc_date": doc_date or today_str(),
                "created_at": now_str(),
                "updated_at": now_str(),
            })
            for line in lines:
                line["doc_id"] = doc_id
                self.db.insert("sales_items", line)

        self.audit.log("sale.create", user=user, entity=doc_type,
                       entity_id=doc_id, details=f"{number}, {len(lines)} pozitsiya")
        return doc_id

    # ------------------------------------------------------------------ #
    #  O'qish
    # ------------------------------------------------------------------ #

    def get_doc(self, doc_id: int) -> dict:
        """Hujjat + pozitsiyalar + mijoz nomi."""
        doc = self.db.query_one(
            "SELECT d.*, c.name AS customer_name FROM sales_docs d "
            "LEFT JOIN customers c ON c.id = d.customer_id WHERE d.id = ?",
            (doc_id,),
        )
        if not doc:
            raise NotFoundError(f"Hujjat topilmadi (id={doc_id}).")
        items = self.db.query(
            "SELECT i.*, p.name AS product_name, p.unit, p.sku "
            "FROM sales_items i JOIN products p ON p.id = i.product_id "
            "WHERE i.doc_id = ? ORDER BY i.id", (doc_id,)
        )
        return {"doc": doc, "items": items}

    def list_docs(self, page: int = 1, per_page: int = 25,
                  doc_type: str | None = None, status: str | None = None,
                  search: str | None = None, date_from: str | None = None,
                  date_to: str | None = None,
                  customer_id: int | None = None) -> Page:
        """Sahifalangan hujjatlar ro'yxati (filtrlar bilan)."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if doc_type:
            where.append("d.doc_type = ?")
            params.append(doc_type)
        if status:
            where.append("d.status = ?")
            params.append(status)
        if customer_id:
            where.append("d.customer_id = ?")
            params.append(customer_id)
        if date_from:
            where.append("d.doc_date >= ?")
            params.append(date_from)
        if date_to:
            where.append("d.doc_date <= ?")
            params.append(date_to)
        if search:
            where.append("(d.number LIKE ? OR c.name LIKE ?)")
            like = f"%{search.strip()}%"
            params += [like, like]
        cond = " AND ".join(where)
        base = ("FROM sales_docs d LEFT JOIN customers c "
                "ON c.id = d.customer_id WHERE " + cond)
        total = int(self.db.scalar(f"SELECT COUNT(*) {base}", tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT d.*, c.name AS customer_name {base} "
            f"ORDER BY d.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    def recent(self, limit: int = 10) -> list[dict]:
        """Dashboard uchun oxirgi hujjatlar."""
        return self.db.query(
            "SELECT d.id, d.number, d.doc_type, d.status, d.total, d.doc_date, "
            "       c.name AS customer_name "
            "FROM sales_docs d LEFT JOIN customers c ON c.id = d.customer_id "
            "WHERE d.status <> 'cancelled' ORDER BY d.id DESC LIMIT ?",
            (limit,),
        )

    # ------------------------------------------------------------------ #
    #  Holat o'zgarishlari
    # ------------------------------------------------------------------ #

    def confirm(self, doc_id: int, user: dict | None = None) -> None:
        """
        Hujjatni tasdiqlaydi. ``invoice``/``pos`` uchun ombordan chiqim,
        ``return`` uchun omborga kirim qilinadi.
        """
        data = self.get_doc(doc_id)
        doc, items = data["doc"], data["items"]
        if doc["status"] != "draft":
            raise StateError("Faqat qoralama hujjatni tasdiqlash mumkin.")

        inventory = self.container.get("inventory")
        with self.db.transaction():
            if doc["doc_type"] in _STOCK_TYPES:
                for item in items:
                    inventory.move_out(
                        item["product_id"], doc["warehouse_id"],
                        D(item["quantity"]), ref_type=doc["doc_type"],
                        ref_id=doc_id, note=doc["number"], user=user,
                    )
            elif doc["doc_type"] == "return":
                for item in items:
                    inventory.move_in(
                        item["product_id"], doc["warehouse_id"],
                        D(item["quantity"]), ref_type="return",
                        ref_id=doc_id, note=doc["number"], user=user,
                    )
            self.db.update("sales_docs", {
                "status": "confirmed", "updated_at": now_str(),
            }, "id = ?", (doc_id,))

        self.audit.log("sale.confirm", user=user, entity=doc["doc_type"],
                       entity_id=doc_id, details=doc["number"])
        self.bus.emit("sale.confirmed", doc_id=doc_id,
                      doc_type=doc["doc_type"], total=D(doc["total"]),
                      user_id=user.get("id") if user else None)

    def cancel(self, doc_id: int, user: dict | None = None) -> None:
        """Hujjatni bekor qiladi; ombor harakatlari teskari qaytariladi."""
        data = self.get_doc(doc_id)
        doc, items = data["doc"], data["items"]
        if doc["status"] == "cancelled":
            raise StateError("Hujjat allaqachon bekor qilingan.")
        if D(doc["paid_amount"]) > 0:
            raise StateError(
                "To'lov qilingan hujjatni bekor qilib bo'lmaydi — "
                "avval qaytarish (return) hujjatini rasmiylashtiring.")

        inventory = self.container.get("inventory")
        stock_moved = (doc["status"] in ("confirmed", "partial", "paid")
                       and doc["doc_type"] in _STOCK_TYPES + ("return",))
        with self.db.transaction():
            if stock_moved:
                for item in items:
                    if doc["doc_type"] == "return":
                        inventory.move_out(
                            item["product_id"], doc["warehouse_id"],
                            D(item["quantity"]), ref_type="return_cancel",
                            ref_id=doc_id, note=doc["number"], user=user)
                    else:
                        inventory.move_in(
                            item["product_id"], doc["warehouse_id"],
                            D(item["quantity"]), ref_type="sale_cancel",
                            ref_id=doc_id, note=doc["number"], user=user)
            self.db.update("sales_docs", {
                "status": "cancelled", "updated_at": now_str(),
            }, "id = ?", (doc_id,))
        self.audit.log("sale.cancel", user=user, entity=doc["doc_type"],
                       entity_id=doc_id, details=doc["number"])

    def convert(self, doc_id: int, user: dict | None = None) -> int:
        """
        Hujjatni keyingi bosqichga o'tkazadi:
        taklif -> buyurtma -> hisob-faktura. Yangi hujjat ``id`` sini qaytaradi.
        """
        data = self.get_doc(doc_id)
        doc, items = data["doc"], data["items"]
        target = _CONVERT_FLOW.get(doc["doc_type"])
        if not target:
            raise StateError(
                f"{doc['doc_type']} hujjatini konvertatsiya qilib bo'lmaydi.")
        if doc["status"] == "cancelled":
            raise StateError("Bekor qilingan hujjatni konvertatsiya qilib bo'lmaydi.")

        new_items = [{
            "product_id": i["product_id"], "quantity": D(i["quantity"]),
            "price": D(i["price"]), "discount": D(i["discount"]),
        } for i in items]
        new_id = self.create_doc(
            target, doc["customer_id"], doc["warehouse_id"], new_items,
            user=user, note=f"{doc['number']} asosida", discount=D(doc["discount"]),
            parent_id=doc_id,
        )
        self.audit.log("sale.convert", user=user, entity=doc["doc_type"],
                       entity_id=doc_id, details=f"-> {target} #{new_id}")
        return new_id

    def create_return(self, parent_id: int, items: list[dict],
                      user: dict | None = None, note: str = "") -> int:
        """
        Qaytarish hujjati: sotilgan hujjat asosida, miqdorlar cheklangan
        (sotilganidan ko'p qaytarib bo'lmaydi). Darhol tasdiqlanadi.
        """
        data = self.get_doc(parent_id)
        parent, sold_items = data["doc"], data["items"]
        if parent["doc_type"] not in _STOCK_TYPES:
            raise StateError("Faqat hisob-faktura yoki POS savdodan qaytarish mumkin.")
        if parent["status"] not in ("confirmed", "partial", "paid"):
            raise StateError("Faqat tasdiqlangan hujjatdan qaytarish mumkin.")

        sold = {i["product_id"]: D(i["quantity"]) for i in sold_items}
        already = self._returned_quantities(parent_id)
        prices = {i["product_id"]: D(i["price"]) for i in sold_items}

        return_items = []
        for raw in items:
            pid = raw.get("product_id")
            qty = D(raw.get("quantity"))
            if pid not in sold:
                raise ValidationError(f"Mahsulot #{pid} bu hujjatda sotilmagan.")
            if qty <= 0:
                raise ValidationError("Qaytarish miqdori musbat bo'lishi kerak.")
            if qty > sold[pid] - already.get(pid, D(0)):
                raise ValidationError(
                    f"Mahsulot #{pid}: qaytarish miqdori sotilganidan oshib ketdi.")
            return_items.append({
                "product_id": pid, "quantity": qty, "price": prices[pid],
            })

        return_id = self.create_doc(
            "return", parent["customer_id"], parent["warehouse_id"],
            return_items, user=user,
            note=note or f"{parent['number']} bo'yicha qaytarish",
            parent_id=parent_id,
        )
        self.confirm(return_id, user=user)
        return return_id

    def register_payment(self, doc_id: int, amount, method: str = "cash",
                         user: dict | None = None) -> None:
        """
        To'lovni hujjatga qayd etadi (kassa/bank yozuvi 3-bosqichdagi
        PaymentService orqali; bu metod hujjat holatini yuritadi).
        """
        doc = self.get_doc(doc_id)["doc"]
        if doc["doc_type"] not in ("invoice", "pos", "order"):
            raise StateError("Bu turdagi hujjatga to'lov qabul qilinmaydi.")
        if doc["status"] not in ("confirmed", "partial"):
            raise StateError("Faqat tasdiqlangan hujjatga to'lov qabul qilinadi.")
        pay = D(amount)
        if pay <= 0:
            raise ValidationError("To'lov summasi musbat bo'lishi kerak.")
        remaining = D(doc["total"]) - D(doc["paid_amount"])
        if pay > remaining:
            raise ValidationError(
                f"To'lov qoldiqdan oshib ketdi (qoldiq: {remaining}).")
        new_paid = D(doc["paid_amount"]) + pay
        status = "paid" if new_paid >= D(doc["total"]) else "partial"
        self.db.update("sales_docs", {
            "paid_amount": new_paid, "status": status, "updated_at": now_str(),
        }, "id = ?", (doc_id,))
        self.audit.log("sale.payment", user=user, entity=doc["doc_type"],
                       entity_id=doc_id, details=f"{pay} ({method})")
        self.bus.emit("sale.payment", doc_id=doc_id, amount=pay,
                      method=method, user_id=user.get("id") if user else None)

    # ------------------------------------------------------------------ #
    #  POS — tezkor kassa savdosi
    # ------------------------------------------------------------------ #

    def pos_sale(self, items: list[dict], user: dict | None = None,
                 customer_id: int | None = None,
                 warehouse_id: int | None = None,
                 method: str = "cash", discount=0) -> dict:
        """
        Kassa savdosi: yaratish + tasdiqlash + to'liq to'lov bir qadamda.

        3-bosqichda PaymentService mavjud bo'lsa kassa orderi va
        buxgalteriya o'tkazmasi ham avtomatik yaratiladi.
        """
        doc_id = self.create_doc("pos", customer_id, warehouse_id, items,
                                 user=user, discount=discount)
        self.confirm(doc_id, user=user)
        doc = self.get_doc(doc_id)["doc"]

        payments = self.service("payments")
        if payments is not None:
            payments.receive_for_sale(doc_id, D(doc["total"]),
                                      method=method, user=user)
        else:
            self.register_payment(doc_id, D(doc["total"]),
                                  method=method, user=user)
        return self.get_doc(doc_id)

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _get_customer(self, customer_id: int) -> dict:
        customer = self.db.query_one(
            "SELECT * FROM customers WHERE id = ?", (customer_id,))
        if not customer:
            raise NotFoundError(f"Mijoz topilmadi (id={customer_id}).")
        return customer

    def _build_lines(self, items: list[dict],
                     customer: dict | None) -> list[dict]:
        """Pozitsiyalarni tekshiradi, chegirma va QQS ni hisoblaydi."""
        if not items:
            raise ValidationError("Hujjatda kamida bitta pozitsiya bo'lishi kerak.")
        customer_discount = D(customer["discount_percent"]) if customer else D(0)
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
            price = D(raw.get("price", product["sale_price"]))
            if price < 0:
                raise ValidationError(f"{product['name']}: narx manfiy bo'lmasin.")

            line_discount = D(raw.get("discount", 0))
            gross = D(qty * price)
            if line_discount == 0 and customer_discount > 0:
                line_discount = D(gross * customer_discount / 100)
            if line_discount < 0 or line_discount > gross:
                raise ValidationError(
                    f"{product['name']}: chegirma 0 dan {gross} gacha bo'lsin.")

            total = D(gross - line_discount)
            vat_rate = D(raw.get("vat_rate", product["vat_rate"]))
            vat_amount = (D(total * vat_rate / (100 + vat_rate))
                          if vat_rate > 0 else D(0))
            lines.append({
                "product_id": product["id"],
                "quantity": qty,
                "price": price,
                "discount": line_discount,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "total": total,
            })
        return lines

    @staticmethod
    def _totals(lines: list[dict], doc_discount: Decimal) -> dict:
        """Hujjat jami summalarini hisoblaydi (hujjat chegirmasi bilan)."""
        subtotal = D(sum((line["total"] for line in lines), Decimal("0")))
        vat_sum = D(sum((line["vat_amount"] for line in lines), Decimal("0")))
        if doc_discount < 0 or doc_discount > subtotal:
            raise ValidationError(
                f"Hujjat chegirmasi 0 dan {subtotal} gacha bo'lishi kerak.")
        total = D(subtotal - doc_discount)
        # Chegirma qo'llanganda QQS proporsional kamayadi
        vat_amount = (D(vat_sum * total / subtotal)
                      if subtotal > 0 else D(0))
        return {"subtotal": subtotal, "discount": doc_discount,
                "vat_amount": vat_amount, "total": total}

    def _returned_quantities(self, parent_id: int) -> dict[int, Decimal]:
        """Hujjat bo'yicha ilgari qaytarilgan miqdorlar (mahsulot kesimida)."""
        rows = self.db.query(
            "SELECT i.product_id, SUM(i.quantity) AS qty "
            "FROM sales_docs d JOIN sales_items i ON i.doc_id = d.id "
            "WHERE d.parent_id = ? AND d.doc_type = 'return' "
            "AND d.status <> 'cancelled' GROUP BY i.product_id",
            (parent_id,),
        )
        return {r["product_id"]: D(r["qty"]) for r in rows}
