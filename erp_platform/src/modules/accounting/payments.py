# -*- coding: utf-8 -*-
"""
To'lovlar servisi — kassa va bank operatsiyalari.

Har bir to'lov:
  1. ``payments`` jadvaliga yoziladi (kassa kitobi / bank ko'chirmasi)
  2. Jurnal o'tkazmasi yaratiladi (dvoyna zapis)
  3. Bog'langan hujjatning (savdo/xarid) to'lov holatini yangilaydi

To'lov usuli -> pul hisobi: ``cash`` -> 5010 (kassa),
``bank``/``card``/``click``/``payme``/``uzum`` -> 5110 (hisob-kitob raqami).
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, ValidationError
from src.core.utils import (
    D, clamp_page, next_document_number, now_str, Page, today_str,
)
from src.modules.base import BaseService

PAYMENT_METHODS = ("cash", "bank", "card", "click", "payme", "uzum")
_CASH_CODE, _BANK_CODE = "5010", "5110"


class PaymentService(BaseService):
    """Pul kirim-chiqimlarini boshqaruvchi servis."""

    # ------------------------------------------------------------------ #
    #  Umumiy to'lov yaratish
    # ------------------------------------------------------------------ #

    def create_payment(self, payment_type: str, amount, method: str = "cash",
                       corr_account: str | int | None = None,
                       partner_type: str = "", partner_id: int | None = None,
                       ref_type: str = "", ref_id: int | None = None,
                       note: str = "", payment_date: str | None = None,
                       user: dict | None = None) -> int:
        """
        Universal to'lov: ``in`` (kirim) yoki ``out`` (chiqim).

        ``corr_account`` — korrespondent hisob kodi (masalan xarajat 9410,
        debitor 4010). Jurnal: kirimda Dt pul / Kt korr; chiqimda teskari.
        """
        if payment_type not in ("in", "out"):
            raise ValidationError(f"Noma'lum to'lov turi: {payment_type}")
        if method not in PAYMENT_METHODS:
            raise ValidationError(f"Noma'lum to'lov usuli: {method}")
        pay = D(amount)
        if pay <= 0:
            raise ValidationError("To'lov summasi musbat bo'lishi kerak.")

        accounting = self.container.get("accounting")
        money_code = self.money_account_code(method)
        money_account = accounting.account_by_code(money_code)
        corr_id = None
        if corr_account is not None:
            corr = (accounting.account_by_code(str(corr_account))
                    if not isinstance(corr_account, int)
                    else self.db.query_one(
                        "SELECT * FROM accounts WHERE id = ?", (corr_account,)))
            if not corr:
                raise NotFoundError(f"Korr. hisob topilmadi: {corr_account}")
            corr_id = corr["id"]

        with self.db.transaction():
            number = next_document_number(self.db, "PAY")
            payment_id = self.db.insert("payments", {
                "number": number,
                "payment_type": payment_type,
                "method": method,
                "account_id": money_account["id"],
                "corr_account_id": corr_id,
                "partner_type": partner_type,
                "partner_id": partner_id,
                "ref_type": ref_type,
                "ref_id": ref_id,
                "amount": pay,
                "payment_date": payment_date or today_str(),
                "note": note,
                "user_id": user.get("id") if user else None,
                "created_at": now_str(),
            })
            if corr_id is not None:
                if payment_type == "in":
                    lines = [
                        {"account": money_code, "debit": pay},
                        {"account": corr_id, "credit": pay,
                         "partner_type": partner_type, "partner_id": partner_id},
                    ]
                else:
                    lines = [
                        {"account": corr_id, "debit": pay,
                         "partner_type": partner_type, "partner_id": partner_id},
                        {"account": money_code, "credit": pay},
                    ]
                accounting.create_entry(
                    f"To'lov {number}" + (f" ({note})" if note else ""),
                    lines, entry_date=payment_date or today_str(),
                    ref_type="payment", ref_id=payment_id, user=user)

        self.audit.log("payment.create", user=user, entity="payment",
                       entity_id=payment_id,
                       details=f"{number}: {payment_type} {pay} ({method})")
        self.bus.emit("payment.created", payment_id=payment_id,
                      payment_type=payment_type, amount=pay, method=method)
        return payment_id

    # ------------------------------------------------------------------ #
    #  Maxsus stsenariylar
    # ------------------------------------------------------------------ #

    def receive_for_sale(self, doc_id: int, amount, method: str = "cash",
                         user: dict | None = None) -> int:
        """Savdo hujjati bo'yicha pul qabul qilish (Dt pul / Kt 4010)."""
        sales = self.container.get("sales")
        doc = sales.get_doc(doc_id)["doc"]
        payment_id = self.create_payment(
            "in", amount, method=method, corr_account="4010",
            partner_type="customer", partner_id=doc["customer_id"],
            ref_type="sale", ref_id=doc_id,
            note=f"{doc['number']} bo'yicha to'lov", user=user)
        sales.register_payment(doc_id, amount, method=method, user=user)
        return payment_id

    def pay_for_purchase(self, purchase_id: int, amount,
                         method: str = "bank",
                         user: dict | None = None) -> int:
        """Xarid bo'yicha ta'minotchiga to'lov (Dt 6010 / Kt pul)."""
        purchases = self.container.get("purchases")
        doc = purchases.get(purchase_id)["doc"]
        payment_id = self.create_payment(
            "out", amount, method=method, corr_account="6010",
            partner_type="supplier", partner_id=doc["supplier_id"],
            ref_type="purchase", ref_id=purchase_id,
            note=f"{doc['number']} bo'yicha to'lov", user=user)
        purchases.register_payment(purchase_id, amount, user=user)
        return payment_id

    def expense(self, amount, note: str, method: str = "cash",
                expense_account: str = "9410",
                user: dict | None = None) -> int:
        """Xarajat to'lovi (Dt xarajat / Kt pul)."""
        return self.create_payment(
            "out", amount, method=method, corr_account=expense_account,
            ref_type="expense", note=note, user=user)

    def other_income(self, amount, note: str, method: str = "cash",
                     income_account: str = "9010",
                     user: dict | None = None) -> int:
        """Boshqa daromad kirimi (Dt pul / Kt daromad)."""
        return self.create_payment(
            "in", amount, method=method, corr_account=income_account,
            ref_type="income", note=note, user=user)

    # ------------------------------------------------------------------ #
    #  Qoldiqlar va kassa kitobi
    # ------------------------------------------------------------------ #

    def money_account_code(self, method: str) -> str:
        """To'lov usuliga mos pul hisobi kodi."""
        return _CASH_CODE if method == "cash" else _BANK_CODE

    def cash_balance(self) -> Decimal:
        """Kassadagi qoldiq (5010, jurnal bo'yicha)."""
        return self.container.get("accounting").account_balance(_CASH_CODE)

    def bank_balance(self) -> Decimal:
        """Bankdagi qoldiq (5110, jurnal bo'yicha)."""
        return self.container.get("accounting").account_balance(_BANK_CODE)

    def cashbook(self, page: int = 1, per_page: int = 25,
                 method: str | None = None,
                 payment_type: str | None = None,
                 date_from: str | None = None,
                 date_to: str | None = None) -> Page:
        """Kassa kitobi / to'lovlar jurnali (filtrlar bilan)."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if method == "cash":
            where.append("p.method = 'cash'")
        elif method == "bank":
            where.append("p.method <> 'cash'")
        if payment_type:
            where.append("p.payment_type = ?")
            params.append(payment_type)
        if date_from:
            where.append("p.payment_date >= ?")
            params.append(date_from)
        if date_to:
            where.append("p.payment_date <= ?")
            params.append(date_to)
        cond = " AND ".join(where)
        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM payments p WHERE {cond}",
            tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT p.*, a.name AS account_name, ca.code AS corr_code, "
            f"       ca.name AS corr_name "
            f"FROM payments p "
            f"LEFT JOIN accounts a ON a.id = p.account_id "
            f"LEFT JOIN accounts ca ON ca.id = p.corr_account_id "
            f"WHERE {cond} ORDER BY p.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page))
        return Page(items=items, page=page, per_page=per_page, total=total)

    def cash_flow(self, date_from: str, date_to: str) -> dict:
        """Pul oqimi hisoboti: kirimlar va chiqimlar (usul kesimida)."""
        rows = self.db.query(
            "SELECT payment_type, method, SUM(amount) AS total "
            "FROM payments WHERE payment_date >= ? AND payment_date <= ? "
            "GROUP BY payment_type, method ORDER BY payment_type, method",
            (date_from, date_to))
        inflow = D(sum((D(r["total"]) for r in rows
                        if r["payment_type"] == "in"), Decimal("0")))
        outflow = D(sum((D(r["total"]) for r in rows
                         if r["payment_type"] == "out"), Decimal("0")))
        return {
            "date_from": date_from, "date_to": date_to, "rows": rows,
            "inflow": inflow, "outflow": outflow,
            "net": D(inflow - outflow),
            "cash_balance": self.cash_balance(),
            "bank_balance": self.bank_balance(),
        }
