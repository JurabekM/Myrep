# -*- coding: utf-8 -*-
"""
Ish haqi (payroll) servisi.

Hisoblash (O'zbekiston, soddalashtirilgan):
  * Yalpi (gross)   — xodimning oylik maoshi
  * Daromad solig'i — gross * ``accounting.income_tax_rate`` (standart 12%)
  * INPS badali     — gross * ``accounting.pension_rate`` (standart 0.1%)
  * Sof (net)       — gross - soliq - INPS

Hayot sikli: ``draft`` -> ``approved`` (jurnal: Dt 9410 / Kt 6710, Kt 6410)
-> ``paid`` (to'lov: Dt 6710 / Kt kassa yoki bank).
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, StateError, ValidationError
from src.core.utils import D, now_str, Page, clamp_page
from src.modules.base import BaseService


class PayrollService(BaseService):
    """Oylik ish haqi hisob-kitobi va to'lovi."""

    # ------------------------------------------------------------------ #
    #  Hisoblash
    # ------------------------------------------------------------------ #

    def create_run(self, period: str, user: dict | None = None) -> int:
        """
        Davr (``YYYY-MM``) uchun ish haqi vedomosti yaratadi.

        Barcha faol xodimlar bo'yicha soliqlar hisoblanadi; vedomost
        ``draft`` holatida saqlanadi.
        """
        if len(period) != 7 or period[4] != "-":
            raise ValidationError("Davr formati YYYY-MM bo'lishi kerak.")
        if self.db.query_one(
                "SELECT id FROM payroll_runs WHERE period = ?", (period,)):
            raise StateError(f"{period} davri uchun vedomost allaqachon mavjud.")

        employees = self.db.query(
            "SELECT * FROM employees WHERE status = 'active' AND salary > 0")
        if not employees:
            raise ValidationError("Maoshi belgilangan faol xodimlar topilmadi.")

        tax_rate = D(self.config.get("accounting.income_tax_rate", 12))
        pension_rate = D(self.config.get("accounting.pension_rate", 0.1))

        total_gross = total_tax = total_net = D(0)
        with self.db.transaction():
            run_id = self.db.insert("payroll_runs", {
                "period": period, "status": "draft",
                "total_gross": 0, "total_tax": 0, "total_net": 0,
                "created_by": user.get("id") if user else None,
                "created_at": now_str(),
            })
            for employee in employees:
                gross = D(employee["salary"])
                income_tax = D(gross * tax_rate / 100)
                pension = D(gross * pension_rate / 100)
                net = D(gross - income_tax - pension)
                self.db.insert("payroll_items", {
                    "run_id": run_id,
                    "employee_id": employee["id"],
                    "gross": gross,
                    "income_tax": income_tax,
                    "pension": pension,
                    "other_deductions": 0,
                    "net": net,
                    "note": "",
                })
                total_gross += gross
                total_tax += income_tax + pension
                total_net += net
            self.db.update("payroll_runs", {
                "total_gross": D(total_gross),
                "total_tax": D(total_tax),
                "total_net": D(total_net),
            }, "id = ?", (run_id,))

        self.audit.log("payroll.create", user=user, entity="payroll",
                       entity_id=run_id,
                       details=f"{period}: {len(employees)} xodim, "
                               f"jami {total_gross}")
        return run_id

    def get_run(self, run_id: int) -> dict:
        """Vedomost + satrlari (xodim nomlari bilan)."""
        run = self.db.query_one(
            "SELECT * FROM payroll_runs WHERE id = ?", (run_id,))
        if not run:
            raise NotFoundError(f"Vedomost topilmadi (id={run_id}).")
        items = self.db.query(
            "SELECT i.*, e.full_name, e.code, e.position "
            "FROM payroll_items i JOIN employees e ON e.id = i.employee_id "
            "WHERE i.run_id = ? ORDER BY e.full_name", (run_id,))
        return {"run": run, "items": items}

    def list_runs(self, page: int = 1, per_page: int = 25) -> Page:
        """Vedomostlar ro'yxati (yangi -> eski)."""
        page, per_page = clamp_page(page, per_page)
        total = int(self.db.scalar(
            "SELECT COUNT(*) FROM payroll_runs", (), 0) or 0)
        items = self.db.query(
            "SELECT * FROM payroll_runs ORDER BY period DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page))
        return Page(items=items, page=page, per_page=per_page, total=total)

    def update_item(self, run_id: int, item_id: int,
                    other_deductions=None, note: str | None = None,
                    user: dict | None = None) -> None:
        """Draft vedomostda qo'shimcha ushlanmalarni tahrirlaydi."""
        run = self.get_run(run_id)["run"]
        if run["status"] != "draft":
            raise StateError("Faqat qoralama vedomostni tahrirlash mumkin.")
        item = self.db.query_one(
            "SELECT * FROM payroll_items WHERE id = ? AND run_id = ?",
            (item_id, run_id))
        if not item:
            raise NotFoundError("Vedomost satri topilmadi.")
        payload: dict = {}
        if other_deductions is not None:
            deduction = D(other_deductions)
            if deduction < 0:
                raise ValidationError("Ushlanma manfiy bo'lishi mumkin emas.")
            new_net = D(D(item["gross"]) - D(item["income_tax"])
                        - D(item["pension"]) - deduction)
            if new_net < 0:
                raise ValidationError("Ushlanmalar yalpi maoshdan oshib ketdi.")
            payload.update({"other_deductions": deduction, "net": new_net})
        if note is not None:
            payload["note"] = note
        if payload:
            self.db.update("payroll_items", payload, "id = ?", (item_id,))
            self._recalc_totals(run_id)

    # ------------------------------------------------------------------ #
    #  Tasdiqlash va to'lash
    # ------------------------------------------------------------------ #

    def approve(self, run_id: int, user: dict | None = None) -> None:
        """
        Vedomostni tasdiqlaydi va buxgalteriya o'tkazmasini yozadi:
        Dt 9410 (xarajat) / Kt 6710 (xodimlarga qarz), Kt 6410 (soliqlar).
        """
        run = self.get_run(run_id)["run"]
        if run["status"] != "draft":
            raise StateError("Faqat qoralama vedomostni tasdiqlash mumkin.")
        gross, tax = D(run["total_gross"]), D(run["total_tax"])
        other = D(self.db.scalar(
            "SELECT SUM(other_deductions) FROM payroll_items WHERE run_id = ?",
            (run_id,), 0))
        net = D(run["total_net"])

        accounting = self.container.get("accounting")
        lines = [
            {"account": "9410", "debit": gross},
            {"account": "6710", "credit": D(net + other)},
            {"account": "6410", "credit": tax},
        ]
        # boshqa ushlanmalar ham 6710 da qoladi (kompaniya hisobida)
        accounting.create_entry(
            f"Ish haqi {run['period']}", lines,
            entry_date=f"{run['period']}-28", ref_type="payroll",
            ref_id=run_id, user=user)

        self.db.update("payroll_runs", {"status": "approved"},
                       "id = ?", (run_id,))
        self.audit.log("payroll.approve", user=user, entity="payroll",
                       entity_id=run_id, details=run["period"])

    def pay(self, run_id: int, method: str = "bank",
            user: dict | None = None) -> int:
        """
        Tasdiqlangan vedomost bo'yicha sof maoshni to'laydi
        (Dt 6710 / Kt kassa yoki bank). To'lov ``id`` sini qaytaradi.
        """
        run = self.get_run(run_id)["run"]
        if run["status"] != "approved":
            raise StateError("Faqat tasdiqlangan vedomostni to'lash mumkin.")
        payments = self.container.get("payments")
        payment_id = payments.create_payment(
            "out", D(run["total_net"]), method=method,
            corr_account="6710", ref_type="payroll", ref_id=run_id,
            note=f"Ish haqi {run['period']}", user=user)
        self.db.update("payroll_runs", {"status": "paid"},
                       "id = ?", (run_id,))
        self.audit.log("payroll.pay", user=user, entity="payroll",
                       entity_id=run_id, details=run["period"])
        return payment_id

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _recalc_totals(self, run_id: int) -> None:
        """Vedomost jami summalarini satrlardan qayta hisoblaydi."""
        row = self.db.query_one(
            "SELECT SUM(gross) AS g, SUM(income_tax + pension) AS t, "
            "SUM(net) AS n FROM payroll_items WHERE run_id = ?", (run_id,))
        self.db.update("payroll_runs", {
            "total_gross": D(row["g"] if row else 0),
            "total_tax": D(row["t"] if row else 0),
            "total_net": D(row["n"] if row else 0),
        }, "id = ?", (run_id,))
