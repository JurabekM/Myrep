# -*- coding: utf-8 -*-
"""
Buxgalteriya servisi — dvoyna zapis (double-entry) yadrosi.

* Hisoblar rejasi (O'zbekiston NAS-21 asosida, soddalashtirilgan)
* Jurnal o'tkazmalari: har bir o'tkazmada debet = kredit tengligi majburiy
* Avtomatik o'tkazmalar (hodisalar orqali):
    - savdo tasdiqlanganda:  Dt 4010 / Kt 9010, Kt 6520 (QQS)  + tannarx:
      Dt 9110 / Kt 2900
    - qaytarishda: teskari o'tkazmalar
    - xarid qabulida: Dt 2900 (netto), Dt 4410 (kirim QQS) / Kt 6010
* Moliyaviy hisobotlar: aylanma qaydnoma (trial balance), balans,
  foyda-zarar, QQS hisoboti

Pul yozuvlari (kassa/bank) :mod:`payments` servisida yaratiladi.
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, ValidationError
from src.core.utils import (
    D, clamp_page, next_document_number, now_str, Page, today_str,
)
from src.modules.base import BaseService

#: Debet-normal hisob turlari (qoldiq = debet - kredit)
_DEBIT_NORMAL = ("asset", "expense")


class AccountingService(BaseService):
    """Jurnal, hisoblar rejasi va moliyaviy hisobotlar."""

    def __init__(self, container) -> None:
        super().__init__(container)
        # Avtomatik o'tkazmalar uchun hodisalarga obuna (Observer pattern)
        self.bus.subscribe("sale.confirmed", self._on_sale_confirmed)
        self.bus.subscribe("purchase.received", self._on_purchase_received)

    # ------------------------------------------------------------------ #
    #  Hisoblar rejasi
    # ------------------------------------------------------------------ #

    def accounts(self, only_active: bool = True) -> list[dict]:
        """Hisoblar rejasi ro'yxati (kod tartibida)."""
        where = "WHERE is_active = 1" if only_active else ""
        return self.db.query(f"SELECT * FROM accounts {where} ORDER BY code")

    def account_by_code(self, code: str) -> dict:
        """Hisobni kodi bo'yicha qaytaradi; topilmasa xato."""
        account = self.db.query_one(
            "SELECT * FROM accounts WHERE code = ?", (str(code),))
        if not account:
            raise NotFoundError(f"Hisob topilmadi (kod={code}).")
        return account

    def create_account(self, code: str, name: str, acc_type: str,
                       user: dict | None = None, is_cash: int = 0,
                       is_bank: int = 0) -> int:
        """Hisoblar rejasiga yangi hisob qo'shadi."""
        code = str(code).strip()
        if not code or not name.strip():
            raise ValidationError("Hisob kodi va nomi bo'sh bo'lishi mumkin emas.")
        if acc_type not in ("asset", "contra_asset", "liability", "equity",
                            "income", "expense"):
            raise ValidationError(f"Noma'lum hisob turi: {acc_type}")
        if self.db.query_one("SELECT id FROM accounts WHERE code = ?", (code,)):
            raise ValidationError(f"{code} kodli hisob allaqachon mavjud.")
        account_id = self.db.insert("accounts", {
            "code": code, "name": name.strip(), "type": acc_type,
            "is_cash": is_cash, "is_bank": is_bank, "is_active": 1,
        })
        self.audit.log("account.create", user=user, entity="account",
                       entity_id=account_id, details=f"{code} {name}")
        return account_id

    # ------------------------------------------------------------------ #
    #  Jurnal o'tkazmalari
    # ------------------------------------------------------------------ #

    def create_entry(self, memo: str, lines: list[dict],
                     entry_date: str | None = None, ref_type: str = "",
                     ref_id: int | None = None,
                     user: dict | None = None) -> int:
        """
        Jurnal o'tkazmasi yaratadi.

        ``lines``: ``[{"account": "4010", "debit": 100}, {"account": "9010",
        "credit": 100}, ...]`` — ``account`` kod yoki id bo'lishi mumkin.

        :raises ValidationError: debet va kredit jami teng bo'lmasa.
        """
        if not lines or len(lines) < 2:
            raise ValidationError(
                "O'tkazmada kamida ikkita satr bo'lishi kerak.")

        normalized = []
        total_debit = total_credit = D(0)
        for raw in lines:
            account_id = self._resolve_account_id(raw.get("account"))
            debit, credit = D(raw.get("debit", 0)), D(raw.get("credit", 0))
            if debit < 0 or credit < 0:
                raise ValidationError("Debet/kredit manfiy bo'lishi mumkin emas.")
            if (debit > 0) == (credit > 0):
                raise ValidationError(
                    "Har bir satrda faqat debet YOKI kredit bo'lishi kerak.")
            total_debit += debit
            total_credit += credit
            normalized.append({
                "account_id": account_id, "debit": debit, "credit": credit,
                "partner_type": raw.get("partner_type", ""),
                "partner_id": raw.get("partner_id"),
            })

        if total_debit != total_credit:
            raise ValidationError(
                f"Balans buzildi: debet {total_debit} != kredit {total_credit}.")
        if total_debit == 0:
            raise ValidationError("O'tkazma summasi nolga teng bo'lishi mumkin emas.")

        with self.db.transaction():
            number = next_document_number(self.db, "JRN")
            entry_id = self.db.insert("journal_entries", {
                "number": number,
                "entry_date": entry_date or today_str(),
                "memo": memo,
                "ref_type": ref_type,
                "ref_id": ref_id,
                "user_id": user.get("id") if user else None,
                "is_posted": 1,
                "created_at": now_str(),
            })
            for line in normalized:
                line["entry_id"] = entry_id
                self.db.insert("journal_lines", line)

        self.audit.log("journal.post", user=user, entity="journal",
                       entity_id=entry_id, details=f"{number}: {memo}")
        return entry_id

    def get_entry(self, entry_id: int) -> dict:
        """O'tkazma + satrlari (hisob nomlari bilan)."""
        entry = self.db.query_one(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,))
        if not entry:
            raise NotFoundError(f"O'tkazma topilmadi (id={entry_id}).")
        lines = self.db.query(
            "SELECT l.*, a.code AS account_code, a.name AS account_name "
            "FROM journal_lines l JOIN accounts a ON a.id = l.account_id "
            "WHERE l.entry_id = ? ORDER BY l.id", (entry_id,))
        return {"entry": entry, "lines": lines}

    def list_entries(self, page: int = 1, per_page: int = 25,
                     date_from: str | None = None, date_to: str | None = None,
                     ref_type: str | None = None,
                     search: str | None = None) -> Page:
        """Jurnal o'tkazmalari ro'yxati (umumiy summa bilan)."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if date_from:
            where.append("e.entry_date >= ?")
            params.append(date_from)
        if date_to:
            where.append("e.entry_date <= ?")
            params.append(date_to)
        if ref_type:
            where.append("e.ref_type = ?")
            params.append(ref_type)
        if search:
            where.append("(e.number LIKE ? OR e.memo LIKE ?)")
            like = f"%{search.strip()}%"
            params += [like, like]
        cond = " AND ".join(where)
        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM journal_entries e WHERE {cond}",
            tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT e.*, (SELECT SUM(debit) FROM journal_lines l "
            f"WHERE l.entry_id = e.id) AS amount "
            f"FROM journal_entries e WHERE {cond} "
            f"ORDER BY e.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page))
        return Page(items=items, page=page, per_page=per_page, total=total)

    # ------------------------------------------------------------------ #
    #  Qoldiqlar va hisobotlar
    # ------------------------------------------------------------------ #

    def account_balance(self, code: str, date_to: str | None = None) -> Decimal:
        """
        Hisob qoldig'i (normal tomonga nisbatan musbat).

        Aktiv/xarajat: debet - kredit; passiv/kapital/daromad: kredit - debet.
        """
        account = self.account_by_code(code)
        where, params = ["l.account_id = ?"], [account["id"]]
        if date_to:
            where.append("e.entry_date <= ?")
            params.append(date_to)
        row = self.db.query_one(
            "SELECT SUM(l.debit) AS d, SUM(l.credit) AS c "
            "FROM journal_lines l JOIN journal_entries e ON e.id = l.entry_id "
            f"WHERE {' AND '.join(where)} AND e.is_posted = 1", tuple(params))
        debit, credit = D(row["d"] if row else 0), D(row["c"] if row else 0)
        if account["type"] in _DEBIT_NORMAL:
            return D(debit - credit)
        return D(credit - debit)

    def trial_balance(self, date_to: str | None = None) -> list[dict]:
        """Aylanma qaydnoma: har bir hisob bo'yicha aylanma va qoldiq."""
        where, params = ["e.is_posted = 1"], []
        if date_to:
            where.append("e.entry_date <= ?")
            params.append(date_to)
        rows = self.db.query(
            "SELECT a.code, a.name, a.type, "
            "       COALESCE(t.d, 0) AS total_debit, "
            "       COALESCE(t.c, 0) AS total_credit "
            "FROM accounts a "
            "LEFT JOIN (SELECT l.account_id, SUM(l.debit) AS d, "
            "                  SUM(l.credit) AS c "
            "           FROM journal_lines l "
            "           JOIN journal_entries e ON e.id = l.entry_id "
            f"          WHERE {' AND '.join(where)} "
            "           GROUP BY l.account_id) t ON t.account_id = a.id "
            "WHERE a.is_active = 1 ORDER BY a.code", tuple(params))
        result = []
        for row in rows:
            debit, credit = D(row["total_debit"]), D(row["total_credit"])
            balance = (debit - credit if row["type"] in _DEBIT_NORMAL
                       else credit - debit)
            result.append({**row, "total_debit": debit,
                           "total_credit": credit, "balance": D(balance)})
        return result

    def profit_loss(self, date_from: str, date_to: str) -> dict:
        """Foyda-zarar hisoboti: davr daromadlari, xarajatlari, sof natija."""
        rows = self.db.query(
            "SELECT a.code, a.name, a.type, "
            "       COALESCE(SUM(l.credit - l.debit), 0) AS net_credit "
            "FROM accounts a "
            "JOIN journal_lines l ON l.account_id = a.id "
            "JOIN journal_entries e ON e.id = l.entry_id "
            "WHERE a.type IN ('income', 'expense') AND e.is_posted = 1 "
            "  AND e.entry_date >= ? AND e.entry_date <= ? "
            "GROUP BY a.id, a.code, a.name, a.type ORDER BY a.code",
            (date_from, date_to))
        income_rows, expense_rows = [], []
        total_income = total_expense = D(0)
        for row in rows:
            if row["type"] == "income":
                amount = D(row["net_credit"])
                total_income += amount
                income_rows.append({"code": row["code"], "name": row["name"],
                                    "amount": amount})
            else:
                amount = D(-D(row["net_credit"]))
                total_expense += amount
                expense_rows.append({"code": row["code"], "name": row["name"],
                                     "amount": amount})
        return {
            "date_from": date_from, "date_to": date_to,
            "income": income_rows, "expenses": expense_rows,
            "total_income": D(total_income),
            "total_expense": D(total_expense),
            "net_profit": D(total_income - total_expense),
        }

    def balance_sheet(self, date_to: str | None = None) -> dict:
        """
        Buxgalteriya balansi: Aktiv = Majburiyat + Kapital.

        Joriy davr sof foydasi kapital bo'limiga qo'shiladi.
        """
        date_to = date_to or today_str()
        tb = self.trial_balance(date_to)
        assets, liabilities, equity = [], [], []
        total_assets = total_liabilities = total_equity = D(0)
        net_profit = D(0)

        for row in tb:
            balance = row["balance"]
            if row["type"] == "asset":
                if balance != 0:
                    assets.append(row)
                total_assets += balance
            elif row["type"] == "contra_asset":
                if balance != 0:
                    assets.append({**row, "balance": D(-balance)})
                total_assets -= balance
            elif row["type"] == "liability":
                if balance != 0:
                    liabilities.append(row)
                total_liabilities += balance
            elif row["type"] == "equity":
                if balance != 0:
                    equity.append(row)
                total_equity += balance
            else:  # income/expense — davr natijasi
                net_profit += balance if row["type"] == "income" else -balance

        if net_profit != 0:
            equity.append({"code": "----", "name": "Joriy davr sof foydasi",
                           "type": "equity", "balance": D(net_profit)})
        total_equity += net_profit

        return {
            "date_to": date_to,
            "assets": assets, "liabilities": liabilities, "equity": equity,
            "total_assets": D(total_assets),
            "total_liabilities": D(total_liabilities),
            "total_equity": D(total_equity),
            "balanced": D(total_assets) == D(total_liabilities + total_equity),
        }

    def vat_report(self, date_from: str, date_to: str) -> dict:
        """
        QQS hisoboti: chiqim QQS (savdo) - kirim QQS (xarid) = to'lanadigan QQS.
        """
        output_vat = D(self.db.scalar(
            "SELECT SUM(CASE WHEN doc_type = 'return' THEN -vat_amount "
            "ELSE vat_amount END) FROM sales_docs "
            "WHERE doc_type IN ('invoice', 'pos', 'return') "
            "  AND status IN ('confirmed', 'partial', 'paid') "
            "  AND doc_date >= ? AND doc_date <= ?",
            (date_from, date_to), 0))
        input_vat = D(self.db.scalar(
            "SELECT SUM(vat_amount) FROM purchases "
            "WHERE status IN ('received', 'partial', 'paid') "
            "  AND doc_date >= ? AND doc_date <= ?",
            (date_from, date_to), 0))
        return {
            "date_from": date_from, "date_to": date_to,
            "output_vat": output_vat, "input_vat": input_vat,
            "payable": D(output_vat - input_vat),
            "rate": D(self.config.get("accounting.vat_rate", 12)),
        }

    # ------------------------------------------------------------------ #
    #  Avtomatik o'tkazmalar (hodisa ishlovchilari)
    # ------------------------------------------------------------------ #

    def _on_sale_confirmed(self, doc_id: int, doc_type: str,
                           total: Decimal, user_id: int | None = None,
                           **_: object) -> None:
        """Savdo tasdiqlanganda daromad + QQS + tannarx o'tkazmalari."""
        if doc_type not in ("invoice", "pos", "return"):
            return
        sales = self.service("sales")
        if sales is None:
            return
        data = sales.get_doc(doc_id)
        doc, items = data["doc"], data["items"]
        vat = D(doc["vat_amount"])
        total = D(doc["total"])
        net = D(total - vat)
        user = {"id": user_id, "username": "system"} if user_id else None

        cost = D(0)
        for item in items:
            product = self.db.query_one(
                "SELECT cost_price FROM products WHERE id = ?",
                (item["product_id"],))
            cost += D(D(item["quantity"]) * D(product["cost_price"] if product else 0))

        if doc_type == "return":
            lines = [
                {"account": "9010", "debit": net},
                {"account": "6520", "debit": vat} if vat > 0 else None,
                {"account": "4010", "credit": total,
                 "partner_type": "customer", "partner_id": doc["customer_id"]},
            ]
            lines = [ln for ln in lines if ln]
            self.create_entry(f"Qaytarish {doc['number']}", lines,
                              entry_date=doc["doc_date"], ref_type="sale_return",
                              ref_id=doc_id, user=user)
            if cost > 0:
                self.create_entry(
                    f"Qaytarish tannarxi {doc['number']}",
                    [{"account": "2900", "debit": cost},
                     {"account": "9110", "credit": cost}],
                    entry_date=doc["doc_date"], ref_type="sale_return_cogs",
                    ref_id=doc_id, user=user)
            return

        lines = [
            {"account": "4010", "debit": total,
             "partner_type": "customer", "partner_id": doc["customer_id"]},
            {"account": "9010", "credit": net},
        ]
        if vat > 0:
            lines.append({"account": "6520", "credit": vat})
        self.create_entry(f"Savdo {doc['number']}", lines,
                          entry_date=doc["doc_date"], ref_type="sale",
                          ref_id=doc_id, user=user)
        if cost > 0:
            self.create_entry(
                f"Tannarx {doc['number']}",
                [{"account": "9110", "debit": cost},
                 {"account": "2900", "credit": cost}],
                entry_date=doc["doc_date"], ref_type="sale_cogs",
                ref_id=doc_id, user=user)

    def _on_purchase_received(self, purchase_id: int, total: Decimal,
                              user_id: int | None = None,
                              **_: object) -> None:
        """Xarid qabulida: Dt 2900 (netto) + Dt 4410 (QQS) / Kt 6010."""
        purchases = self.service("purchases")
        if purchases is None:
            return
        doc = purchases.get(purchase_id)["doc"]
        total = D(doc["total"])
        vat = D(doc["vat_amount"])
        net = D(total - vat)
        user = {"id": user_id, "username": "system"} if user_id else None

        lines = [{"account": "2900", "debit": net}]
        if vat > 0:
            lines.append({"account": "4410", "debit": vat})
        lines.append({"account": "6010", "credit": total,
                      "partner_type": "supplier",
                      "partner_id": doc["supplier_id"]})
        self.create_entry(f"Xarid {doc['number']}", lines,
                          entry_date=doc["doc_date"], ref_type="purchase",
                          ref_id=purchase_id, user=user)

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _resolve_account_id(self, account) -> int:
        """Hisob kodi yoki id sini ``accounts.id`` ga aylantiradi."""
        if account is None:
            raise ValidationError("O'tkazma satrida hisob ko'rsatilmagan.")
        if isinstance(account, int):
            row = self.db.query_one(
                "SELECT id FROM accounts WHERE id = ?", (account,))
        else:
            row = self.db.query_one(
                "SELECT id FROM accounts WHERE code = ?", (str(account),))
        if not row:
            raise NotFoundError(f"Hisob topilmadi: {account}")
        return int(row["id"])
