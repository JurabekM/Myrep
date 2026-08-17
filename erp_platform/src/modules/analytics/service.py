# -*- coding: utf-8 -*-
"""
Analitika servisi.

* KPI: oy daromadi, o'sish, o'rtacha chek, yalpi marja, yangi mijozlar
* Prognoz: chiziqli regressiya (eng kichik kvadratlar) — sof Python
* TOP mijozlar / TOP mahsulotlar
* ABC tahlil: daromad bo'yicha (A — 80%, B — 95%, C — qolgan)
* XYZ tahlil: talab barqarorligi (variatsiya koeffitsienti bo'yicha)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.core.utils import D, last_n_months, month_bounds, today_str
from src.modules.base import BaseService

_REVENUE_STATUSES = "('confirmed', 'partial', 'paid')"


class AnalyticsService(BaseService):
    """Biznes analitikasi va prognozlar."""

    # ------------------------------------------------------------------ #
    #  KPI
    # ------------------------------------------------------------------ #

    def kpi(self) -> dict:
        """Joriy oy KPI to'plami (o'tgan oy bilan taqqoslash)."""
        today = date.today()
        cur_start, cur_end = month_bounds(today.year, today.month)
        prev_year, prev_month = (today.year, today.month - 1) \
            if today.month > 1 else (today.year - 1, 12)
        prev_start, prev_end = month_bounds(prev_year, prev_month)

        cur = self._period_stats(cur_start, cur_end)
        prev = self._period_stats(prev_start, prev_end)

        growth = D(0)
        if prev["revenue"] > 0:
            growth = D((cur["revenue"] - prev["revenue"]) * 100 / prev["revenue"])

        new_customers = int(self.db.scalar(
            "SELECT COUNT(*) FROM customers WHERE created_at >= ?",
            (cur_start,), 0) or 0)

        return {
            "period": cur_start[:7],
            "revenue": cur["revenue"],
            "prev_revenue": prev["revenue"],
            "growth_percent": growth,
            "orders": cur["orders"],
            "avg_check": cur["avg_check"],
            "gross_margin": cur["margin"],
            "new_customers": new_customers,
        }

    def _period_stats(self, date_from: str, date_to: str) -> dict:
        """Davr bo'yicha: daromad, hujjatlar soni, o'rtacha chek, marja."""
        row = self.db.query_one(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(total), 0) AS revenue "
            "FROM sales_docs WHERE doc_type IN ('invoice', 'pos') "
            f"AND status IN {_REVENUE_STATUSES} "
            "AND doc_date >= ? AND doc_date <= ?", (date_from, date_to))
        orders = int(row["orders"]) if row else 0
        revenue = D(row["revenue"] if row else 0)

        cost = D(self.db.scalar(
            "SELECT SUM(i.quantity * p.cost_price) FROM sales_items i "
            "JOIN sales_docs d ON d.id = i.doc_id "
            "JOIN products p ON p.id = i.product_id "
            "WHERE d.doc_type IN ('invoice', 'pos') "
            f"AND d.status IN {_REVENUE_STATUSES} "
            "AND d.doc_date >= ? AND d.doc_date <= ?",
            (date_from, date_to), 0))
        margin = D(0)
        if revenue > 0:
            margin = D((revenue - cost) * 100 / revenue)
        return {
            "revenue": revenue,
            "orders": orders,
            "avg_check": D(revenue / orders) if orders else D(0),
            "margin": margin,
        }

    # ------------------------------------------------------------------ #
    #  Trend va prognoz
    # ------------------------------------------------------------------ #

    def revenue_trend(self, months: int = 12) -> list[dict]:
        """Oylik daromad seriyasi (grafik va prognoz asosi)."""
        series = []
        for year, month in last_n_months(months):
            start, end = month_bounds(year, month)
            revenue = D(self.db.scalar(
                "SELECT SUM(CASE WHEN doc_type = 'return' THEN -total "
                "ELSE total END) FROM sales_docs "
                "WHERE doc_type IN ('invoice', 'pos', 'return') "
                f"AND status IN {_REVENUE_STATUSES} "
                "AND doc_date >= ? AND doc_date <= ?", (start, end), 0))
            series.append({"period": f"{year:04d}-{month:02d}",
                           "revenue": revenue})
        return series

    def forecast(self, horizon: int = 3, history_months: int = 12) -> dict:
        """
        Daromad prognozi — chiziqli regressiya (eng kichik kvadratlar).

        Kam ma'lumotda (2 oydan kam savdo) o'rtacha qiymatga qaytadi.
        """
        history = self.revenue_trend(history_months)
        ys = [float(row["revenue"]) for row in history]
        n = len(ys)
        nonzero = sum(1 for y in ys if y > 0)

        if nonzero < 2:
            avg = sum(ys) / n if n else 0.0
            predictions = [max(avg, 0.0)] * horizon
        else:
            xs = list(range(1, n + 1))
            sum_x, sum_y = sum(xs), sum(ys)
            sum_xy = sum(x * y for x, y in zip(xs, ys))
            sum_x2 = sum(x * x for x in xs)
            denom = n * sum_x2 - sum_x ** 2
            slope = (n * sum_xy - sum_x * sum_y) / denom if denom else 0.0
            intercept = (sum_y - slope * sum_x) / n
            predictions = [max(slope * (n + k) + intercept, 0.0)
                           for k in range(1, horizon + 1)]

        # Prognoz davrlari nomlari
        last_year, last_month = last_n_months(1)[0]
        labels = []
        year, month = last_year, last_month
        for _ in range(horizon):
            month += 1
            if month == 13:
                month, year = 1, year + 1
            labels.append(f"{year:04d}-{month:02d}")

        return {
            "history": history,
            "forecast": [{"period": label, "revenue": D(value)}
                         for label, value in zip(labels, predictions)],
        }

    # ------------------------------------------------------------------ #
    #  TOP ro'yxatlar
    # ------------------------------------------------------------------ #

    def top_customers(self, limit: int = 10, days: int = 90) -> list[dict]:
        """Daromad bo'yicha TOP mijozlar (oxirgi ``days`` kun)."""
        since = (date.today() - timedelta(days=days)).isoformat()
        return self.db.query(
            "SELECT c.id, c.name, COUNT(d.id) AS orders, "
            "       SUM(d.total) AS revenue "
            "FROM sales_docs d JOIN customers c ON c.id = d.customer_id "
            "WHERE d.doc_type IN ('invoice', 'pos') "
            f"AND d.status IN {_REVENUE_STATUSES} AND d.doc_date >= ? "
            "GROUP BY c.id, c.name ORDER BY revenue DESC LIMIT ?",
            (since, limit))

    def top_products(self, limit: int = 10, days: int = 90) -> list[dict]:
        """Daromad bo'yicha TOP mahsulotlar (oxirgi ``days`` kun)."""
        since = (date.today() - timedelta(days=days)).isoformat()
        return self.db.query(
            "SELECT p.id, p.name, p.unit, SUM(i.quantity) AS qty, "
            "       SUM(i.total) AS revenue "
            "FROM sales_items i "
            "JOIN sales_docs d ON d.id = i.doc_id "
            "JOIN products p ON p.id = i.product_id "
            "WHERE d.doc_type IN ('invoice', 'pos') "
            f"AND d.status IN {_REVENUE_STATUSES} AND d.doc_date >= ? "
            "GROUP BY p.id, p.name, p.unit ORDER BY revenue DESC LIMIT ?",
            (since, limit))

    # ------------------------------------------------------------------ #
    #  ABC / XYZ tahlil
    # ------------------------------------------------------------------ #

    def abc_analysis(self, days: int = 90) -> list[dict]:
        """
        ABC tahlil: mahsulotlar daromadga qo'shgan hissasi bo'yicha.

        A — jami daromadning 80% igacha, B — 95% igacha, C — qolganlari.
        """
        rows = self.top_products(limit=100000, days=days)
        total = D(sum((D(r["revenue"]) for r in rows), Decimal("0")))
        cumulative = D(0)
        result = []
        for row in rows:
            revenue = D(row["revenue"])
            # Baholash JORIY mahsulotgacha yig'ilgan ulush bo'yicha —
            # shunda eng katta hissali mahsulot doim "A" oladi.
            prev_share = D(cumulative * 100 / total) if total > 0 else D(0)
            cumulative += revenue
            share = D(revenue * 100 / total) if total > 0 else D(0)
            cum_share = D(cumulative * 100 / total) if total > 0 else D(0)
            grade = "A" if prev_share < 80 else ("B" if prev_share < 95 else "C")
            result.append({**row, "revenue": revenue, "share": share,
                           "cumulative_share": cum_share, "grade": grade})
        return result

    def xyz_analysis(self, months: int = 6) -> list[dict]:
        """
        XYZ tahlil: oylik sotuv miqdorining barqarorligi.

        Variatsiya koeffitsienti (CV = std/mean):
        X — CV <= 10% (barqaror), Y — CV <= 25%, Z — undan yuqori (tartibsiz).
        """
        periods = [f"{y:04d}-{m:02d}" for y, m in last_n_months(months)]
        rows = self.db.query(
            "SELECT p.id, p.name, SUBSTR(d.doc_date, 1, 7) AS period, "
            "       SUM(i.quantity) AS qty "
            "FROM sales_items i "
            "JOIN sales_docs d ON d.id = i.doc_id "
            "JOIN products p ON p.id = i.product_id "
            "WHERE d.doc_type IN ('invoice', 'pos') "
            f"AND d.status IN {_REVENUE_STATUSES} "
            "AND SUBSTR(d.doc_date, 1, 7) >= ? "
            "GROUP BY p.id, p.name, SUBSTR(d.doc_date, 1, 7)",
            (periods[0],))

        by_product: dict[int, dict] = {}
        for row in rows:
            entry = by_product.setdefault(
                row["id"], {"id": row["id"], "name": row["name"], "series": {}})
            entry["series"][row["period"]] = float(row["qty"])

        result = []
        for entry in by_product.values():
            values = [entry["series"].get(p, 0.0) for p in periods]
            mean = sum(values) / len(values)
            if mean <= 0:
                continue
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            cv = (variance ** 0.5) / mean
            grade = "X" if cv <= 0.10 else ("Y" if cv <= 0.25 else "Z")
            result.append({
                "id": entry["id"], "name": entry["name"],
                "mean_qty": D(mean), "cv_percent": D(cv * 100),
                "grade": grade,
            })
        result.sort(key=lambda r: r["cv_percent"])
        return result
