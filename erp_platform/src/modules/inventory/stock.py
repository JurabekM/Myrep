# -*- coding: utf-8 -*-
"""
Ombor (stock) servisi.

* Har bir ombor kesimida mahsulot qoldiqlari
* Kirim / chiqim / ko'chirish (transfer) / tuzatish (adjust) harakatlari —
  barchasi ``stock_moves`` jurnalida iz qoldiradi
* Inventarizatsiya (sanoq): kutilgan va haqiqiy qoldiqlar solishtiruvi
* Ombor qiymati (qoldiq * tannarx)

Barcha qoldiq o'zgarishlari Python ``Decimal`` bilan hisoblanadi va
tranzaksiya ichida bajariladi.
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import (
    InsufficientStockError,
    NotFoundError,
    StateError,
    ValidationError,
)
from src.core.utils import D, next_document_number, now_str, Page, clamp_page
from src.modules.base import BaseService


class InventoryService(BaseService):
    """Ombor qoldiqlari va harakatlarini boshqaruvchi servis."""

    # ------------------------------------------------------------------ #
    #  Omborlar
    # ------------------------------------------------------------------ #

    def warehouses(self) -> list[dict]:
        """Faol omborlar ro'yxati."""
        return self.db.query(
            "SELECT * FROM warehouses WHERE is_active = 1 ORDER BY id"
        )

    def default_warehouse_id(self) -> int:
        """Standart (birinchi) ombor identifikatori."""
        row = self.db.query_one(
            "SELECT id FROM warehouses WHERE is_active = 1 ORDER BY id LIMIT 1"
        )
        if not row:
            raise NotFoundError("Hech qanday ombor topilmadi.")
        return int(row["id"])

    def create_warehouse(self, name: str, address: str = "",
                         user: dict | None = None) -> int:
        """Yangi ombor qo'shadi."""
        name = (name or "").strip()
        if not name:
            raise ValidationError("Ombor nomi bo'sh bo'lishi mumkin emas.")
        warehouse_id = self.db.insert(
            "warehouses", {"name": name, "address": address, "is_active": 1}
        )
        self.audit.log("warehouse.create", user=user, entity="warehouse",
                       entity_id=warehouse_id, details=name)
        return warehouse_id

    # ------------------------------------------------------------------ #
    #  Qoldiqlar
    # ------------------------------------------------------------------ #

    def stock_level(self, product_id: int, warehouse_id: int) -> Decimal:
        """Bitta ombor kesimidagi qoldiq."""
        value = self.db.scalar(
            "SELECT quantity FROM stock WHERE product_id = ? AND warehouse_id = ?",
            (product_id, warehouse_id), 0,
        )
        return D(value)

    def total_stock(self, product_id: int) -> Decimal:
        """Mahsulotning barcha omborlardagi jami qoldig'i."""
        value = self.db.scalar(
            "SELECT SUM(quantity) FROM stock WHERE product_id = ?",
            (product_id,), 0,
        )
        return D(value)

    def stock_overview(self, page: int = 1, per_page: int = 25,
                       search: str | None = None,
                       warehouse_id: int | None = None) -> Page:
        """
        Qoldiqlar jadvali: mahsulot, qoldiq, tannarx qiymati, min. zaxira bayrog'i.
        """
        page, per_page = clamp_page(page, per_page)
        where, params = ["p.is_active = 1"], []
        if warehouse_id:
            where.append(
                "EXISTS (SELECT 1 FROM stock st WHERE st.product_id = p.id "
                "AND st.warehouse_id = ?)")
            params.append(warehouse_id)
        if search:
            where.append("(p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?)")
            like = f"%{search.strip()}%"
            params += [like, like, like]

        qty_sql = ("(SELECT COALESCE(SUM(quantity), 0) FROM stock st "
                   "WHERE st.product_id = p.id" +
                   (" AND st.warehouse_id = ?" if warehouse_id else "") + ")")
        qty_params = [warehouse_id] if warehouse_id else []
        cond = " AND ".join(where)

        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM products p WHERE {cond}", tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT p.id, p.sku, p.barcode, p.name, p.unit, p.min_stock, "
            f"       p.cost_price, p.sale_price, {qty_sql} AS quantity "
            f"FROM products p WHERE {cond} "
            f"ORDER BY p.name LIMIT ? OFFSET ?",
            tuple(qty_params) + tuple(params) + (per_page, (page - 1) * per_page),
        )
        for row in items:
            row["stock_value"] = D(row["quantity"]) * D(row["cost_price"])
            row["is_low"] = (D(row["min_stock"]) > 0
                             and D(row["quantity"]) <= D(row["min_stock"]))
        return Page(items=items, page=page, per_page=per_page, total=total)

    def stock_value(self) -> Decimal:
        """Butun ombor qiymati (qoldiq * tannarx)."""
        rows = self.db.query(
            "SELECT s.quantity, p.cost_price FROM stock s "
            "JOIN products p ON p.id = s.product_id WHERE s.quantity <> 0"
        )
        return D(sum((D(r["quantity"]) * D(r["cost_price"]) for r in rows),
                     Decimal("0")))

    # ------------------------------------------------------------------ #
    #  Harakatlar (kirim/chiqim/transfer/tuzatish)
    # ------------------------------------------------------------------ #

    def move_in(self, product_id: int, warehouse_id: int, quantity,
                unit_cost=0, ref_type: str = "", ref_id: int | None = None,
                note: str = "", user: dict | None = None) -> None:
        """Kirim: omborga mahsulot qo'shadi va harakat yozuvini qoldiradi."""
        qty = self._positive_qty(quantity)
        with self.db.transaction():
            self._change_stock(product_id, warehouse_id, qty)
            self._record_move("in", product_id, None, warehouse_id, qty,
                              D(unit_cost), ref_type, ref_id, note, user)
        self.bus.emit("stock.updated", product_id=product_id)

    def move_out(self, product_id: int, warehouse_id: int, quantity,
                 ref_type: str = "", ref_id: int | None = None,
                 note: str = "", user: dict | None = None) -> None:
        """Chiqim: qoldiq yetarliligini tekshirib mahsulotni kamaytiradi."""
        qty = self._positive_qty(quantity)
        with self.db.transaction():
            self._ensure_available(product_id, warehouse_id, qty)
            self._change_stock(product_id, warehouse_id, -qty)
            self._record_move("out", product_id, warehouse_id, None, qty,
                              D(0), ref_type, ref_id, note, user)
        self.bus.emit("stock.updated", product_id=product_id)

    def transfer(self, product_id: int, warehouse_from: int, warehouse_to: int,
                 quantity, note: str = "", user: dict | None = None) -> None:
        """Ko'chirish: bir ombordan boshqasiga (bitta tranzaksiyada)."""
        if warehouse_from == warehouse_to:
            raise ValidationError("Bir xil ombor orasida ko'chirish mumkin emas.")
        qty = self._positive_qty(quantity)
        with self.db.transaction():
            self._ensure_available(product_id, warehouse_from, qty)
            self._change_stock(product_id, warehouse_from, -qty)
            self._change_stock(product_id, warehouse_to, qty)
            self._record_move("transfer", product_id, warehouse_from,
                              warehouse_to, qty, D(0), "transfer", None, note, user)
        self.audit.log("stock.transfer", user=user, entity="product",
                       entity_id=product_id,
                       details=f"{qty} dona: {warehouse_from} -> {warehouse_to}")
        self.bus.emit("stock.updated", product_id=product_id)

    def adjust(self, product_id: int, warehouse_id: int, new_quantity,
               note: str = "", user: dict | None = None) -> Decimal:
        """
        Tuzatish: qoldiqni belgilangan qiymatga keltiradi
        (inventarizatsiya natijasi). Farqni qaytaradi.
        """
        new_qty = D(new_quantity)
        if new_qty < 0:
            raise ValidationError("Qoldiq manfiy bo'lishi mumkin emas.")
        with self.db.transaction():
            current = self.stock_level(product_id, warehouse_id)
            diff = new_qty - current
            if diff != 0:
                self._change_stock(product_id, warehouse_id, diff)
                self._record_move("adjust", product_id,
                                  warehouse_id if diff < 0 else None,
                                  warehouse_id if diff > 0 else None,
                                  abs(diff), D(0), "adjust", None, note, user)
        if diff != 0:
            self.audit.log("stock.adjust", user=user, entity="product",
                           entity_id=product_id,
                           details=f"{current} -> {new_qty} (farq {diff})")
            self.bus.emit("stock.updated", product_id=product_id)
        return diff

    def moves_history(self, page: int = 1, per_page: int = 25,
                      product_id: int | None = None,
                      warehouse_id: int | None = None) -> Page:
        """Harakatlar jurnali (yangi -> eski), mahsulot nomi bilan."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if product_id:
            where.append("m.product_id = ?")
            params.append(product_id)
        if warehouse_id:
            where.append("(m.warehouse_from = ? OR m.warehouse_to = ?)")
            params += [warehouse_id, warehouse_id]
        cond = " AND ".join(where)
        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM stock_moves m WHERE {cond}",
            tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT m.*, p.name AS product_name, p.unit "
            f"FROM stock_moves m JOIN products p ON p.id = m.product_id "
            f"WHERE {cond} ORDER BY m.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    # ------------------------------------------------------------------ #
    #  Inventarizatsiya
    # ------------------------------------------------------------------ #

    def start_count(self, warehouse_id: int, user: dict | None = None) -> int:
        """
        Inventarizatsiyani boshlaydi: ombordagi barcha qoldiqlarning
        rasmiy nusxasini (kutilgan qiymatlar) oladi.
        """
        with self.db.transaction():
            number = next_document_number(self.db, "CNT")
            count_id = self.db.insert("inventory_counts", {
                "number": number, "warehouse_id": warehouse_id,
                "status": "draft", "user_id": user.get("id") if user else None,
                "created_at": now_str(),
            })
            rows = self.db.query(
                "SELECT product_id, quantity FROM stock "
                "WHERE warehouse_id = ? AND quantity <> 0", (warehouse_id,)
            )
            for row in rows:
                self.db.insert("inventory_count_items", {
                    "count_id": count_id,
                    "product_id": row["product_id"],
                    "expected_qty": D(row["quantity"]),
                    "actual_qty": D(row["quantity"]),
                    "difference": 0,
                })
        self.audit.log("inventory.count_start", user=user,
                       entity="inventory_count", entity_id=count_id,
                       details=f"ombor #{warehouse_id}")
        return count_id

    def set_count_item(self, count_id: int, product_id: int, actual_qty) -> None:
        """Sanoq davomida haqiqiy qoldiqni kiritadi."""
        count = self._get_count(count_id)
        if count["status"] != "draft":
            raise StateError("Yakunlangan inventarizatsiyani o'zgartirib bo'lmaydi.")
        actual = D(actual_qty)
        if actual < 0:
            raise ValidationError("Haqiqiy qoldiq manfiy bo'lishi mumkin emas.")
        item = self.db.query_one(
            "SELECT * FROM inventory_count_items "
            "WHERE count_id = ? AND product_id = ?", (count_id, product_id)
        )
        if item:
            self.db.update("inventory_count_items", {
                "actual_qty": actual,
                "difference": actual - D(item["expected_qty"]),
            }, "id = ?", (item["id"],))
        else:
            self.db.insert("inventory_count_items", {
                "count_id": count_id, "product_id": product_id,
                "expected_qty": 0, "actual_qty": actual, "difference": actual,
            })

    def complete_count(self, count_id: int, user: dict | None = None) -> int:
        """
        Inventarizatsiyani yakunlaydi: farqlar bo'yicha qoldiqlar
        tuzatiladi. Tuzatilgan pozitsiyalar sonini qaytaradi.
        """
        count = self._get_count(count_id)
        if count["status"] != "draft":
            raise StateError("Inventarizatsiya allaqachon yakunlangan.")
        items = self.db.query(
            "SELECT * FROM inventory_count_items WHERE count_id = ?", (count_id,)
        )
        adjusted = 0
        for item in items:
            if D(item["difference"]) != 0:
                self.adjust(
                    item["product_id"], count["warehouse_id"],
                    D(item["actual_qty"]),
                    note=f"Inventarizatsiya {count['number']}", user=user,
                )
                adjusted += 1
        self.db.update("inventory_counts", {
            "status": "done", "completed_at": now_str(),
        }, "id = ?", (count_id,))
        self.audit.log("inventory.count_complete", user=user,
                       entity="inventory_count", entity_id=count_id,
                       details=f"{adjusted} ta pozitsiya tuzatildi")
        return adjusted

    def count_details(self, count_id: int) -> dict:
        """Inventarizatsiya hujjati + pozitsiyalari (mahsulot nomlari bilan)."""
        count = self._get_count(count_id)
        items = self.db.query(
            "SELECT i.*, p.name AS product_name, p.unit, p.sku "
            "FROM inventory_count_items i JOIN products p ON p.id = i.product_id "
            "WHERE i.count_id = ? ORDER BY p.name", (count_id,)
        )
        return {"count": count, "items": items}

    def list_counts(self, page: int = 1, per_page: int = 25) -> Page:
        """Inventarizatsiyalar ro'yxati."""
        page, per_page = clamp_page(page, per_page)
        total = int(self.db.scalar(
            "SELECT COUNT(*) FROM inventory_counts", (), 0) or 0)
        items = self.db.query(
            "SELECT c.*, w.name AS warehouse_name FROM inventory_counts c "
            "JOIN warehouses w ON w.id = c.warehouse_id "
            "ORDER BY c.id DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _get_count(self, count_id: int) -> dict:
        count = self.db.query_one(
            "SELECT * FROM inventory_counts WHERE id = ?", (count_id,)
        )
        if not count:
            raise NotFoundError(f"Inventarizatsiya topilmadi (id={count_id}).")
        return count

    @staticmethod
    def _positive_qty(quantity) -> Decimal:
        qty = D(quantity)
        if qty <= 0:
            raise ValidationError("Miqdor musbat bo'lishi kerak.")
        return qty

    def _ensure_available(self, product_id: int, warehouse_id: int,
                          qty: Decimal) -> None:
        """Qoldiq yetarliligini tekshiradi (config ruxsat bersa o'tkazib yuboradi)."""
        if self.config.get("inventory.allow_negative_stock", False):
            return
        current = self.stock_level(product_id, warehouse_id)
        if current < qty:
            product = self.db.query_one(
                "SELECT name, unit FROM products WHERE id = ?", (product_id,)
            )
            name = product["name"] if product else f"#{product_id}"
            raise InsufficientStockError(
                f"Omborda yetarli emas: {name} — qoldiq {current}, kerak {qty}."
            )

    def _change_stock(self, product_id: int, warehouse_id: int,
                      delta: Decimal) -> None:
        """
        Qoldiqni Decimal aniqlikda o'zgartiradi.

        Global ulanish qulfi tufayli SELECT+UPDATE juftligi atomar bajariladi.
        """
        row = self.db.query_one(
            "SELECT id, quantity FROM stock "
            "WHERE product_id = ? AND warehouse_id = ?",
            (product_id, warehouse_id),
        )
        if row:
            self.db.update("stock", {"quantity": D(row["quantity"]) + delta},
                           "id = ?", (row["id"],))
        else:
            self.db.insert("stock", {
                "product_id": product_id, "warehouse_id": warehouse_id,
                "quantity": delta,
            })

    def _record_move(self, move_type: str, product_id: int,
                     warehouse_from: int | None, warehouse_to: int | None,
                     qty: Decimal, unit_cost: Decimal, ref_type: str,
                     ref_id: int | None, note: str,
                     user: dict | None) -> None:
        """Harakat jurnaliga yozuv qo'shadi."""
        self.db.insert("stock_moves", {
            "move_type": move_type,
            "product_id": product_id,
            "warehouse_from": warehouse_from,
            "warehouse_to": warehouse_to,
            "quantity": qty,
            "unit_cost": unit_cost,
            "ref_type": ref_type,
            "ref_id": ref_id,
            "note": note,
            "user_id": user.get("id") if user else None,
            "created_at": now_str(),
        })
