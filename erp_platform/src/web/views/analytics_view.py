# -*- coding: utf-8 -*-
"""Analitika sahifasi: KPI, trend + prognoz, TOP ro'yxatlar, ABC/XYZ, heatmap."""
from __future__ import annotations

from flask import abort

from src.core.security import escape_html as e
from src.web import helpers as h
from src.web import svg_charts as charts


def register(app, ctx) -> None:
    """Analitika marshruti."""
    from src.web.server import render
    S = ctx.services

    @app.get("/analytics")
    def analytics_page():
        if not h.can("analytics.view"):
            abort(403)
        analytics = S.get("analytics")
        kpi = analytics.kpi()
        forecast = analytics.forecast(3)
        top_customers = analytics.top_customers(8)
        top_products = analytics.top_products(8)
        abc = analytics.abc_analysis()[:15]
        xyz = analytics.xyz_analysis()[:15]

        growth = kpi["growth_percent"]
        growth_txt = f"{'+' if growth >= 0 else ''}{growth}%"
        kpi_html = f"""
        <div class="grid cols-4">
          {h.stat_card("Oy daromadi", h.m(kpi['revenue']),
                       f"o'tgan oy: {h.m(kpi['prev_revenue'])}", "accent")}
          {h.stat_card("O'sish", growth_txt, "oyma-oy",
                       "green" if growth >= 0 else "red")}
          {h.stat_card("O'rtacha chek", h.m(kpi['avg_check']),
                       f"{kpi['orders']} ta hujjat")}
          {h.stat_card("Yalpi marja", f"{kpi['gross_margin']}%",
                       f"yangi mijozlar: {kpi['new_customers']}", "green")}
        </div>"""

        # Trend + prognoz grafigi (prognoz punktir emas — alohida seriya)
        history = forecast["history"]
        fc = forecast["forecast"]
        labels = [r["period"][2:] for r in history] + \
                 [r["period"][2:] for r in fc]
        hist_values = [r["revenue"] for r in history] + [None] * len(fc)
        fc_values = [None] * (len(history) - 1) + \
                    ([history[-1]["revenue"]] if history else []) + \
                    [r["revenue"] for r in fc]
        # None qiymatlarni 0 bilan emas, oxirgi qiymat bilan davom ettirmaymiz —
        # soddalik uchun ikkita seriyani alohida chizamiz
        trend_chart = charts.line_chart(labels, [
            {"name": "Daromad", "values": [v or 0 for v in hist_values]},
            {"name": "Prognoz", "values": [v or 0 for v in fc_values],
             "color": "#fbbf24"},
        ])

        top_c_rows = [[e(r["name"]), e(r["orders"]), h.m(r["revenue"])]
                      for r in top_customers]
        top_p_rows = [[e(r["name"]), e(r["qty"]), h.m(r["revenue"])]
                      for r in top_products]

        abc_rows = [[
            e(r["name"]), h.m(r["revenue"]), f'{e(r["share"])}%',
            f'{e(r["cumulative_share"])}%',
            f'<span class="badge {"green" if r["grade"] == "A" else ("amber" if r["grade"] == "B" else "gray")}">{r["grade"]}</span>',
        ] for r in abc]
        xyz_rows = [[
            e(r["name"]), e(r["mean_qty"]), f'{e(r["cv_percent"])}%',
            f'<span class="badge {"green" if r["grade"] == "X" else ("amber" if r["grade"] == "Y" else "red")}">{r["grade"]}</span>',
        ] for r in xyz]

        heat = _sales_heatmap(ctx)

        content = (h.page_head("Analitika") + kpi_html +
                   h.card("Daromad trendi va 3 oylik prognoz",
                          f'<div class="chart-box">{trend_chart}</div>' +
                          charts.legend_html(["Daromad (fakt)",
                                              "Prognoz"])) +
                   f'<div class="grid cols-2 mt">'
                   f'{h.card("TOP mijozlar (90 kun)", h.data_table(["Mijoz", "Buyurtmalar", "Daromad"], top_c_rows, num_cols=(1, 2)))}'
                   f'{h.card("TOP mahsulotlar (90 kun)", h.data_table(["Mahsulot", "Miqdor", "Daromad"], top_p_rows, num_cols=(1, 2)))}'
                   "</div>"
                   f'<div class="grid cols-2 mt">'
                   f'{h.card("ABC tahlil (daromad bo`yicha)", h.data_table(["Mahsulot", "Daromad", "Ulush", "Yig`ma", "Sinf"], abc_rows, num_cols=(1, 2, 3)))}'
                   f'{h.card("XYZ tahlil (talab barqarorligi)", h.data_table(["Mahsulot", "O`rtacha oylik", "CV", "Sinf"], xyz_rows, num_cols=(1, 2)))}'
                   "</div>" +
                   h.card("Savdo faolligi (hafta kuni × soat)",
                          f'<div class="chart-box">{heat}</div>'))
        return render(ctx, "Analitika", content, "/analytics")


def _sales_heatmap(ctx) -> str:
    """Hafta kuni × soat kesimida savdolar soni (oxirgi 90 kun)."""
    rows = ctx.db.query(
        "SELECT created_at FROM sales_docs "
        "WHERE doc_type IN ('invoice', 'pos') AND status <> 'cancelled' "
        "AND created_at IS NOT NULL ORDER BY id DESC LIMIT 5000")
    day_names = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]
    matrix = [[0.0] * 24 for _ in range(7)]
    from datetime import datetime

    for row in rows:
        try:
            dt = datetime.strptime(str(row["created_at"])[:19],
                                   "%Y-%m-%d %H:%M:%S")
            matrix[dt.weekday()][dt.hour] += 1
        except (ValueError, TypeError):
            continue
    hours = [f"{hh:02d}" for hh in range(24)]
    return charts.heatmap(day_names, hours, matrix)
