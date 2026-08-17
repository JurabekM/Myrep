# -*- coding: utf-8 -*-
"""Dashboard sahifasi: KPI kartalar, grafiklar, oxirgi hujjatlar."""
from __future__ import annotations

from flask import abort

from src.core.security import escape_html as e
from src.core.utils import money
from src.web import helpers as h
from src.web import svg_charts as charts


def register(app, ctx) -> None:
    """Dashboard marshruti."""
    from src.web.server import render

    @app.get("/")
    def dashboard_page():
        if not h.can("dashboard.view"):
            abort(403)
        reports = ctx.services.get("reports")
        data = reports.dashboard()

        stats = f"""
        <div class="grid cols-4">
          {h.stat_card("Bugungi savdo", h.m(data["today_sales"]), "so'm", "accent")}
          {h.stat_card("Oy savdosi", h.m(data["month_sales"]),
                       f"{data['orders_month']} ta hujjat", "green")}
          {h.stat_card("Oy xarajatlari", h.m(data["month_expenses"]), "so'm", "red")}
          {h.stat_card("Oy foydasi", h.m(data["month_profit"]), "so'm",
                       "green" if data["month_profit"] >= 0 else "red")}
        </div>
        <div class="grid cols-4 mt">
          {h.stat_card("Kassa", h.m(data["cash_balance"]), "5010")}
          {h.stat_card("Bank", h.m(data["bank_balance"]), "5110")}
          {h.stat_card("Ombor qiymati", h.m(data["stock_value"]),
                       f"kam zaxira: {data['low_stock_count']} ta",
                       "amber" if data["low_stock_count"] else "")}
          {h.stat_card("Debitorlik", h.m(data["receivables"]),
                       f"kreditorlik: {money(data['payables'])}")}
        </div>"""

        series = data["monthly_series"]
        labels = [s["period"][2:] for s in series]
        line = charts.line_chart(labels, [
            {"name": "Daromad", "values": [s["revenue"] for s in series]},
            {"name": "Xarajat", "values": [s["expense"] for s in series]},
        ])
        bars = charts.bar_chart(labels, [
            {"name": "Foyda", "values": [s["profit"] for s in series],
             "color": "#34d399"},
        ])
        donut_items = [{"label": h.DOC_TYPE_LABELS.get(r["doc_type"],
                                                       r["doc_type"]),
                        "value": r["total"]}
                       for r in data["sales_by_type"]]
        donut = charts.donut_chart(donut_items or
                                   [{"label": "Bo'sh", "value": 0}])
        donut_legend = charts.legend_html(
            [f"{item['label']}" for item in donut_items] or ["Ma'lumot yo'q"])

        charts_html = f"""
        <div class="grid cols-2 mt">
          {h.card("Daromad va xarajat (12 oy)",
                  f'<div class="chart-box">{line}</div>' +
                  charts.legend_html(["Daromad", "Xarajat"]))}
          {h.card("Oylik foyda",
                  f'<div class="chart-box">{bars}</div>')}
        </div>
        <div class="grid cols-3 mt">
          {h.card("Savdo turlari (joriy oy)",
                  f'<div class="chart-box" style="max-width:230px;margin:auto">'
                  f"{donut}</div>{donut_legend}")}
          {h.card("TOP mahsulotlar (oy)", _top_products_table(data["top_products"]))}
          {h.card("Oxirgi to'lovlar", _payments_table(data["recent_payments"]))}
        </div>
        {h.card("Oxirgi hujjatlar", _recent_sales_table(data["recent_sales"]))}
        """
        content = (h.page_head("Dashboard",
                               h.btn_link("/pos", "POS kassa", "primary")
                               if h.can("pos.operate") else "")
                   + stats + charts_html)
        return render(ctx, "Dashboard", content, "/")


def _top_products_table(rows) -> str:
    return h.data_table(
        ["Mahsulot", "Miqdor", "Daromad"],
        [[e(r["name"]), e(r["qty"]), h.m(r["revenue"])] for r in rows],
        "Bu oyda savdo bo'lmagan", num_cols=(1, 2))


def _payments_table(rows) -> str:
    return h.data_table(
        ["№", "Turi", "Summa"],
        [[e(r["number"]), h.badge(r["payment_type"]), h.m(r["amount"])]
         for r in rows],
        "To'lovlar yo'q", num_cols=(2,))


def _recent_sales_table(rows) -> str:
    return h.data_table(
        ["№", "Turi", "Mijoz", "Holat", "Summa", "Sana"],
        [[h.link(f"/sales/{r['id']}", r["number"]),
          e(h.DOC_TYPE_LABELS.get(r["doc_type"], r["doc_type"])),
          e(r.get("customer_name") or "—"),
          h.badge(r["status"]), h.m(r["total"]), e(r["doc_date"])]
         for r in rows],
        "Hujjatlar yo'q", num_cols=(4,))
