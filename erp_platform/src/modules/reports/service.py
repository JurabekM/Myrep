# -*- coding: utf-8 -*-
"""
Hisobotlar servisi.

Dashboard uchun jamlanma ko'rsatkichlar va operatsion hisobotlar:
savdo, ombor, soliq, HR. Moliyaviy hisobotlar (balans, foyda-zarar)
:mod:`accounting` servisidan olinadi — bu servis ularni bir joyga jamlaydi.

Og'ir so'rovlar 60 soniya keshlanadi.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.utils import D, last_n_months, month_bounds, today_str
from src.modules.base import BaseService

#: Daromad sifatida hisoblanadigan hujjat holatlari
_REVENUE_STATUSES = "('confirmed', 'partial', 'paid')"


class ReportService(BaseService):
    """Dashboard va operatsion hisobotlar."""

    # ------------------------------------------------------------------ #
    #  Dashboard
    # ------------------------------------------------------------------ #

    def dashboard(self) -> dict:
        """
        Bosh sahifa ko'rsatkichlari (60s kesh):
        daromad, xarajat, foyda, kassa/bank, ombor qiymati, debitorlik,
        oxirgi hujjatlar, 12 oylik trend, tur bo'yicha taqsimot.
        """
        return self.cache.get_or_set("reports.dashboard", self._build_dashboard, 60)

    def _build_dashboard(self) -> dict:
        today = today_str()
        month_start, month_end = month_bounds(date.today().year, date.today().month)
        payments = self.service("payments")
        inventory = self.service("inventory")
        accounting = self.service("accounting")

        today_sales = self._net_sales(today, today)
        month_sales = self._net_sales(month_start, month_end)
        pl = (accounting.profit_loss(month_start, month_end)
              if accounting else None)

        receivables = D(self.db.scalar(
            "SELECT SUM(total - paid_amount) FROM sales_docs "
            "WHERE doc_type IN ('invoice', 'pos') "
            f"AND status IN ('confirmed', 'partial')", (), 0))
        payables = D(self.db.scalar(
            "SELECT SUM(total - paid_amount) FROM purchases "
            "WHERE status IN ('received', 'partial')", (), 0))

        return {
            "date": today,
            "today_sales": today_sales,
            "month_sales": month_sales,
            "month_expenses": D(pl["total_expense"]) if pl else D(0),
            "month_profit": D(pl["net_profit"]) if pl else D(0),
            "cash_balance": payments.cash_balance() if payments else D(0),
            "bank_balance": payments.bank_balance() if payments else D(0),
            "stock_value": inventory.stock_value() if inventory else D(0),
            "receivables": receivables,
            "payables": payables,
            "orders_month": int(self.db.scalar(
                "SELECT COUNT(*) FROM sales_docs "
                "WHERE doc_type IN ('invoice', 'pos', 'order') "
                f"AND status IN {_REVENUE_STATUSES} "
                "AND doc_date >= ? AND doc_date <= ?",
                (month_start, month_end), 0) or 0),
            "low_stock_count": len(
                self.service("products").low_stock() if self.service("products") else []),
            "recent_sales": self._recent_sales(6),
            "recent_payments": self._recent_payments(6),
            "monthly_series": self.monthly_series(12),
            "sales_by_type": self._sales_by_type(month_start, month_end),
            "top_products": self._top_products(month_start, month_end, 5),
        }

    def monthly_series(self, months: int = 12) -> list[dict]:
        """Oyma-oy daromad/xarajat/foyda seriyasi (grafiklar uchun)."""
        accounting = self.service("accounting")
        series = []
        for year, month in last_n_months(months):
            start, end = month_bounds(year, month)
            revenue = self._net_sales(start, end)
            expense = D(0)
            if accounting:
                pl = accounting.profit_loss(start, end)
                expense = D(pl["total_expense"])
            series.append({
                "period": f"{year:04d}-{month:02d}",
                "revenue": revenue,
                "expense": expense,
                "profit": D(revenue - expense),
            })
        return series

    # ------------------------------------------------------------------ #
    #  Operatsion hisobotlar
    # ------------------------------------------------------------------ #

    def sales_report(self, date_from: str, date_to: str,
                     group_by: str = "day") -> dict:
        """
        Savdo hisoboti: davr kesimida (kun yoki oy bo'yicha guruhlangan)
        summa, QQS, chegirma, hujjatlar soni; qaytarishlar ayiriladi.
        """
        fmt = 7 if group_by == "month" else 10
        rows = self.db.query(
            "SELECT SUBSTR(doc_date, 1, ?) AS period, "
            "  COUNT(*) AS docs, "
            "  SUM(CASE WHEN doc_type = 'return' THEN -total ELSE total END) AS total, "
            "  SUM(CASE WHEN doc_type = 'return' THEN -vat_amount ELSE vat_amount END) AS vat, "
            "  SUM(CASE WHEN doc_type = 'return' THEN 0 ELSE discount END) AS discount "
            "FROM sales_docs "
            "WHERE doc_type IN ('invoice', 'pos', 'return') "
            f"  AND status IN {_REVENUE_STATUSES} "
            "  AND doc_date >= ? AND doc_date <= ? "
            "GROUP BY SUBSTR(doc_date, 1, ?) ORDER BY period",
            (fmt, date_from, date_to, fmt))
        for row in rows:
            row["total"], row["vat"] = D(row["total"]), D(row["vat"])
            row["discount"] = D(row["discount"])
        return {
            "date_from": date_from, "date_to": date_to, "rows": rows,
            "total": D(sum((r["total"] for r in rows), Decimal("0"))),
            "total_vat": D(sum((r["vat"] for r in rows), Decimal("0"))),
            "total_docs": sum(r["docs"] for r in rows),
        }

    def inventory_report(self) -> dict:
        """Ombor hisoboti: umumiy qiymat, pozitsiyalar, kam zaxira."""
        inventory = self.service("inventory")
        products = self.service("products")
        overview = inventory.stock_overview(page=1, per_page=1000)
        return {
            "stock_value": inventory.stock_value(),
            "positions": overview.total,
            "items": overview.items,
            "low_stock": products.low_stock() if products else [],
        }

    def tax_report(self, date_from: str, date_to: str) -> dict:
        """Soliq hisoboti: QQS + ish haqi soliqlari jamlanmasi."""
        accounting = self.service("accounting")
        vat = accounting.vat_report(date_from, date_to)
        payroll_tax = D(self.db.scalar(
            "SELECT SUM(i.income_tax + i.pension) FROM payroll_items i "
            "JOIN payroll_runs r ON r.id = i.run_id "
            "WHERE r.status IN ('approved', 'paid') "
            "  AND r.period >= ? AND r.period <= ?",
            (date_from[:7], date_to[:7]), 0))
        return {
            "date_from": date_from, "date_to": date_to,
            "vat": vat, "payroll_tax": payroll_tax,
            "total_tax": D(D(vat["payable"]) + payroll_tax),
        }

    def hr_report(self, year: int, month: int) -> dict:
        """HR hisoboti: davomat + oy vedomosti."""
        hr = self.service("hr")
        period = f"{year:04d}-{month:02d}"
        run = self.db.query_one(
            "SELECT * FROM payroll_runs WHERE period = ?", (period,))
        return {
            "period": period,
            "attendance": hr.attendance_sheet(year, month),
            "payroll_run": run,
            "active_employees": int(self.db.scalar(
                "SELECT COUNT(*) FROM employees WHERE status = 'active'",
                (), 0) or 0),
        }

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _net_sales(self, date_from: str, date_to: str) -> Decimal:
        """Sof savdo (qaytarishlar ayirilgan, QQS ichida)."""
        return D(self.db.scalar(
            "SELECT SUM(CASE WHEN doc_type = 'return' THEN -total ELSE total END) "
            "FROM sales_docs WHERE doc_type IN ('invoice', 'pos', 'return') "
            f"AND status IN {_REVENUE_STATUSES} "
            "AND doc_date >= ? AND doc_date <= ?",
            (date_from, date_to), 0))

    def _recent_sales(self, limit: int) -> list[dict]:
        return self.db.query(
            "SELECT d.id, d.number, d.doc_type, d.status, d.total, d.doc_date, "
            "       c.name AS customer_name "
            "FROM sales_docs d LEFT JOIN customers c ON c.id = d.customer_id "
            "WHERE d.status <> 'cancelled' ORDER BY d.id DESC LIMIT ?", (limit,))

    def _recent_payments(self, limit: int) -> list[dict]:
        return self.db.query(
            "SELECT id, number, payment_type, method, amount, payment_date, note "
            "FROM payments ORDER BY id DESC LIMIT ?", (limit,))

    def _sales_by_type(self, date_from: str, date_to: str) -> list[dict]:
        return self.db.query(
            "SELECT doc_type, COUNT(*) AS docs, SUM(total) AS total "
            "FROM sales_docs "
            f"WHERE status IN {_REVENUE_STATUSES} "
            "  AND doc_date >= ? AND doc_date <= ? "
            "GROUP BY doc_type ORDER BY total DESC",
            (date_from, date_to))

    def _top_products(self, date_from: str, date_to: str,
                      limit: int) -> list[dict]:
        return self.db.query(
            "SELECT p.id, p.name, SUM(i.quantity) AS qty, SUM(i.total) AS revenue "
            "FROM sales_items i "
            "JOIN sales_docs d ON d.id = i.doc_id "
            "JOIN products p ON p.id = i.product_id "
            "WHERE d.doc_type IN ('invoice', 'pos') "
            f"  AND d.status IN {_REVENUE_STATUSES} "
            "  AND d.doc_date >= ? AND d.doc_date <= ? "
            "GROUP BY p.id, p.name ORDER BY revenue DESC LIMIT ?",
            (date_from, date_to, limit))
